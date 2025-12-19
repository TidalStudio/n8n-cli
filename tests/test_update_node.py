"""Tests for update-node command."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.update_node import (
    find_node,
    parse_value,
    set_nested_param,
    strip_readonly_fields,
    update_node,
)
from n8n_cli.config import Config
from n8n_cli.main import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide isolated CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_config() -> Config:
    """Provide a valid mock configuration."""
    return Config(api_url="http://localhost:5678", api_key="test-api-key")


@pytest.fixture
def sample_workflow() -> dict[str, Any]:
    """Provide a sample workflow with nodes."""
    return {
        "id": "abc123",
        "name": "Test Workflow",
        "active": False,
        "nodes": [
            {
                "id": "node1",
                "name": "HTTP Request",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {
                    "url": "https://old-url.com",
                    "method": "GET",
                    "options": {
                        "timeout": 10000,
                    },
                },
            },
            {
                "id": "node2",
                "name": "Set",
                "type": "n8n-nodes-base.set",
                "parameters": {
                    "values": {"string": []},
                },
            },
        ],
        "connections": {},
        "updatedAt": "2024-01-15T10:30:00.000Z",
    }


@pytest.fixture
def updated_workflow(sample_workflow: dict[str, Any]) -> dict[str, Any]:
    """Provide a workflow after update."""
    workflow = sample_workflow.copy()
    workflow["updatedAt"] = "2024-01-15T11:00:00.000Z"
    return workflow


class TestFindNode:
    """Tests for find_node helper function."""

    def test_find_by_name(self, sample_workflow: dict[str, Any]) -> None:
        """Test finding a node by name."""
        nodes = sample_workflow["nodes"]
        node = find_node(nodes, node_name="HTTP Request", node_id=None)
        assert node is not None
        assert node["id"] == "node1"

    def test_find_by_id(self, sample_workflow: dict[str, Any]) -> None:
        """Test finding a node by ID."""
        nodes = sample_workflow["nodes"]
        node = find_node(nodes, node_name=None, node_id="node2")
        assert node is not None
        assert node["name"] == "Set"

    def test_not_found_by_name(self, sample_workflow: dict[str, Any]) -> None:
        """Test that None is returned for unknown name."""
        nodes = sample_workflow["nodes"]
        node = find_node(nodes, node_name="Nonexistent", node_id=None)
        assert node is None

    def test_not_found_by_id(self, sample_workflow: dict[str, Any]) -> None:
        """Test that None is returned for unknown ID."""
        nodes = sample_workflow["nodes"]
        node = find_node(nodes, node_name=None, node_id="unknown")
        assert node is None

    def test_empty_nodes_list(self) -> None:
        """Test with empty nodes list."""
        node = find_node([], node_name="Test", node_id=None)
        assert node is None


class TestParseValue:
    """Tests for parse_value helper function."""

    def test_parse_string(self) -> None:
        """Test that plain strings are preserved."""
        assert parse_value("hello world") == "hello world"

    def test_parse_number(self) -> None:
        """Test that numbers are parsed as JSON."""
        assert parse_value("42") == 42
        assert parse_value("3.14") == 3.14

    def test_parse_boolean(self) -> None:
        """Test that booleans are parsed as JSON."""
        assert parse_value("true") is True
        assert parse_value("false") is False

    def test_parse_null(self) -> None:
        """Test that null is parsed as JSON."""
        assert parse_value("null") is None

    def test_parse_array(self) -> None:
        """Test that arrays are parsed as JSON."""
        assert parse_value('[1, 2, 3]') == [1, 2, 3]

    def test_parse_object(self) -> None:
        """Test that objects are parsed as JSON."""
        assert parse_value('{"key": "value"}') == {"key": "value"}

    def test_parse_url_as_string(self) -> None:
        """Test that URLs are treated as strings (not valid JSON)."""
        url = "https://api.example.com/users"
        assert parse_value(url) == url

    def test_parse_quoted_string_as_string(self) -> None:
        """Test that JSON strings result in unquoted strings."""
        assert parse_value('"hello"') == "hello"


class TestStripReadonlyFields:
    """Tests for strip_readonly_fields helper function."""

    def test_strips_id(self) -> None:
        """Test that id field is stripped."""
        workflow = {"id": "abc123", "name": "Test", "nodes": []}
        result = strip_readonly_fields(workflow)
        assert "id" not in result
        assert result["name"] == "Test"

    def test_strips_timestamps(self) -> None:
        """Test that createdAt and updatedAt are stripped."""
        workflow = {
            "name": "Test",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "nodes": [],
        }
        result = strip_readonly_fields(workflow)
        assert "createdAt" not in result
        assert "updatedAt" not in result
        assert result["name"] == "Test"

    def test_strips_all_readonly_fields(self) -> None:
        """Test that all readonly fields are stripped."""
        workflow = {
            "id": "abc123",
            "name": "Test",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "versionId": "v1",
            "isArchived": False,
            "description": "A test workflow",
            "nodes": [],
            "connections": {},
            "active": True,
        }
        result = strip_readonly_fields(workflow)
        assert "id" not in result
        assert "createdAt" not in result
        assert "updatedAt" not in result
        assert "versionId" not in result
        assert "isArchived" not in result
        assert "description" not in result
        # These should remain
        assert result["name"] == "Test"
        assert result["nodes"] == []
        assert result["connections"] == {}
        assert result["active"] is True

    def test_preserves_nodes_and_connections(self) -> None:
        """Test that nodes and connections are preserved."""
        workflow = {
            "id": "abc123",
            "name": "Test",
            "nodes": [{"id": "node1", "name": "Node 1"}],
            "connections": {"Node 1": {}},
        }
        result = strip_readonly_fields(workflow)
        assert result["nodes"] == [{"id": "node1", "name": "Node 1"}]
        assert result["connections"] == {"Node 1": {}}


class TestSetNestedParam:
    """Tests for set_nested_param helper function."""

    def test_set_simple_param(self) -> None:
        """Test setting a simple (non-nested) parameter."""
        params: dict[str, Any] = {"url": "old"}
        set_nested_param(params, "url", "new")
        assert params["url"] == "new"

    def test_set_nested_param(self) -> None:
        """Test setting a nested parameter."""
        params: dict[str, Any] = {"options": {"timeout": 10}}
        set_nested_param(params, "options.timeout", 30)
        assert params["options"]["timeout"] == 30

    def test_create_missing_intermediate(self) -> None:
        """Test creating intermediate dicts when they don't exist."""
        params: dict[str, Any] = {}
        set_nested_param(params, "options.timeout", 30)
        assert params == {"options": {"timeout": 30}}

    def test_deep_nesting(self) -> None:
        """Test deeply nested parameters."""
        params: dict[str, Any] = {}
        set_nested_param(params, "a.b.c.d", "value")
        assert params == {"a": {"b": {"c": {"d": "value"}}}}

    def test_overwrite_non_dict(self) -> None:
        """Test that non-dict intermediate values are overwritten."""
        params: dict[str, Any] = {"options": "not_a_dict"}
        set_nested_param(params, "options.timeout", 30)
        assert params == {"options": {"timeout": 30}}


class TestUpdateNodeCommand:
    """Tests for update-node CLI command."""

    def test_update_by_name_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        updated_workflow: dict[str, Any],
    ) -> None:
        """Test updating a node by name."""
        with (
            patch("n8n_cli.commands.update_node.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.update_node._update_node",
                new_callable=AsyncMock,
                return_value=updated_workflow,
            ) as mock_update,
        ):
            result = cli_runner.invoke(
                update_node,
                ["abc123", "--node-name", "HTTP Request", "--param", "url", "--value", "https://new-url.com"],
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "abc123"
        mock_update.assert_called_once_with(
            api_url="http://localhost:5678",
            api_key="test-api-key",
            workflow_id="abc123",
            node_name="HTTP Request",
            node_id=None,
            param_path="url",
            value="https://new-url.com",
        )

    def test_update_by_id_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        updated_workflow: dict[str, Any],
    ) -> None:
        """Test updating a node by ID."""
        with (
            patch("n8n_cli.commands.update_node.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.update_node._update_node",
                new_callable=AsyncMock,
                return_value=updated_workflow,
            ) as mock_update,
        ):
            result = cli_runner.invoke(
                update_node,
                ["abc123", "--node-id", "node1", "--param", "method", "--value", "POST"],
            )

        assert result.exit_code == 0
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["node_id"] == "node1"
        assert call_kwargs["node_name"] is None

    def test_update_with_json_number(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        updated_workflow: dict[str, Any],
    ) -> None:
        """Test updating with a JSON number value."""
        with (
            patch("n8n_cli.commands.update_node.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.update_node._update_node",
                new_callable=AsyncMock,
                return_value=updated_workflow,
            ) as mock_update,
        ):
            result = cli_runner.invoke(
                update_node,
                ["abc123", "-n", "HTTP Request", "-p", "options.timeout", "-v", "30000"],
            )

        assert result.exit_code == 0
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["value"] == 30000  # Parsed as number

    def test_update_with_json_boolean(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        updated_workflow: dict[str, Any],
    ) -> None:
        """Test updating with a JSON boolean value."""
        with (
            patch("n8n_cli.commands.update_node.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.update_node._update_node",
                new_callable=AsyncMock,
                return_value=updated_workflow,
            ) as mock_update,
        ):
            result = cli_runner.invoke(
                update_node,
                ["abc123", "-n", "HTTP Request", "-p", "options.followRedirects", "-v", "true"],
            )

        assert result.exit_code == 0
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["value"] is True

    def test_update_with_json_object(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        updated_workflow: dict[str, Any],
    ) -> None:
        """Test updating with a JSON object value."""
        with (
            patch("n8n_cli.commands.update_node.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.update_node._update_node",
                new_callable=AsyncMock,
                return_value=updated_workflow,
            ) as mock_update,
        ):
            result = cli_runner.invoke(
                update_node,
                ["abc123", "-n", "Set", "-p", "values", "-v", '{"key": "value"}'],
            )

        assert result.exit_code == 0
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["value"] == {"key": "value"}

    def test_error_both_name_and_id(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that using both --node-name and --node-id returns error."""
        with patch("n8n_cli.commands.update_node.require_config", return_value=mock_config):
            result = cli_runner.invoke(
                cli,
                ["update-node", "abc123", "--node-name", "Test", "--node-id", "node1", "-p", "url", "-v", "val"],
            )

        assert result.exit_code == 1
        assert "Cannot use both" in result.output

    def test_error_neither_name_nor_id(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that omitting both --node-name and --node-id returns error."""
        with patch("n8n_cli.commands.update_node.require_config", return_value=mock_config):
            result = cli_runner.invoke(
                cli,
                ["update-node", "abc123", "-p", "url", "-v", "value"],
            )

        assert result.exit_code == 1
        assert "Must specify either" in result.output

    def test_error_node_not_found(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test error when node is not found."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch("n8n_cli.commands.update_node.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.update_node._update_node",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Node not found: Nonexistent"),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["update-node", "abc123", "-n", "Nonexistent", "-p", "url", "-v", "val"],
            )

        assert result.exit_code == 1
        assert "Node not found" in result.output

    def test_error_workflow_not_found(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test error when workflow is not found."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch("n8n_cli.commands.update_node.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.update_node._update_node",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Workflow not found: xyz999"),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["update-node", "xyz999", "-n", "Test", "-p", "url", "-v", "val"],
            )

        assert result.exit_code == 1
        assert "Workflow not found" in result.output

    def test_error_config_not_set(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test error when config is not set."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.update_node.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(
                cli,
                ["update-node", "abc123", "-n", "Test", "-p", "url", "-v", "val"],
            )

        assert result.exit_code == 2
        assert "Not configured" in result.output

    def test_missing_param_option(self, cli_runner: CliRunner) -> None:
        """Test that --param is required."""
        result = cli_runner.invoke(
            update_node,
            ["abc123", "-n", "Test", "-v", "value"],
        )

        assert result.exit_code != 0
        assert "Missing option" in result.output or "--param" in result.output

    def test_missing_value_option(self, cli_runner: CliRunner) -> None:
        """Test that --value is required."""
        result = cli_runner.invoke(
            update_node,
            ["abc123", "-n", "Test", "-p", "url"],
        )

        assert result.exit_code != 0
        assert "Missing option" in result.output or "--value" in result.output

    def test_command_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test update-node command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "update-node" in result.output

    def test_help_text(self, cli_runner: CliRunner) -> None:
        """Test update-node --help shows usage."""
        result = cli_runner.invoke(update_node, ["--help"])
        assert result.exit_code == 0
        assert "WORKFLOW_ID" in result.output
        assert "--node-name" in result.output
        assert "--node-id" in result.output
        assert "--param" in result.output
        assert "--value" in result.output


class TestUpdateNodeIntegration:
    """Integration tests for _update_node async function."""

    @pytest.mark.asyncio
    async def test_update_node_full_flow(
        self,
        sample_workflow: dict[str, Any],
    ) -> None:
        """Test the full update node flow."""
        from n8n_cli.commands.update_node import _update_node

        updated = sample_workflow.copy()
        updated["nodes"][0]["parameters"]["url"] = "https://new-url.com"

        mock_client = AsyncMock()
        mock_client.get_workflow = AsyncMock(return_value=sample_workflow)
        mock_client.update_workflow = AsyncMock(return_value=updated)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("n8n_cli.commands.update_node.N8nClient", return_value=mock_client):
            result = await _update_node(
                api_url="http://localhost:5678",
                api_key="test-key",
                workflow_id="abc123",
                node_name="HTTP Request",
                node_id=None,
                param_path="url",
                value="https://new-url.com",
            )

        assert result == updated
        mock_client.get_workflow.assert_called_once_with("abc123")
        mock_client.update_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_node_not_found(
        self,
        sample_workflow: dict[str, Any],
    ) -> None:
        """Test NotFoundError when node doesn't exist."""
        from n8n_cli.commands.update_node import _update_node
        from n8n_cli.exceptions import NotFoundError

        mock_client = AsyncMock()
        mock_client.get_workflow = AsyncMock(return_value=sample_workflow)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("n8n_cli.commands.update_node.N8nClient", return_value=mock_client),
            pytest.raises(NotFoundError, match="Node not found: Nonexistent"),
        ):
            await _update_node(
                api_url="http://localhost:5678",
                api_key="test-key",
                workflow_id="abc123",
                node_name="Nonexistent",
                node_id=None,
                param_path="url",
                value="https://new-url.com",
            )

    @pytest.mark.asyncio
    async def test_update_node_creates_parameters_dict(self) -> None:
        """Test that parameters dict is created if missing."""
        from n8n_cli.commands.update_node import _update_node

        workflow_without_params = {
            "id": "abc123",
            "name": "Test",
            "nodes": [
                {"id": "node1", "name": "Test Node", "type": "test"},
            ],
            "connections": {},
        }

        mock_client = AsyncMock()
        mock_client.get_workflow = AsyncMock(return_value=workflow_without_params)
        mock_client.update_workflow = AsyncMock(return_value=workflow_without_params)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("n8n_cli.commands.update_node.N8nClient", return_value=mock_client):
            await _update_node(
                api_url="http://localhost:5678",
                api_key="test-key",
                workflow_id="abc123",
                node_name="Test Node",
                node_id=None,
                param_path="newParam",
                value="newValue",
            )

        # Verify update_workflow was called with the modified workflow
        call_args = mock_client.update_workflow.call_args
        updated_workflow = call_args[0][1]
        assert updated_workflow["nodes"][0]["parameters"] == {"newParam": "newValue"}
