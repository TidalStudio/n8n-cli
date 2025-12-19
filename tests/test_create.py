"""Tests for create workflow command."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.create import create
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
def sample_workflow_input() -> dict[str, Any]:
    """Provide sample workflow input data."""
    return {
        "name": "Test Workflow",
        "nodes": [
            {
                "id": "node1",
                "name": "Start",
                "type": "n8n-nodes-base.start",
                "position": [250, 300],
                "parameters": {},
            }
        ],
        "connections": {},
    }


@pytest.fixture
def sample_workflow_response() -> dict[str, Any]:
    """Provide sample workflow response from API."""
    return {
        "id": "123",
        "name": "Test Workflow",
        "active": False,
        "nodes": [
            {
                "id": "node1",
                "name": "Start",
                "type": "n8n-nodes-base.start",
                "position": [250, 300],
                "parameters": {},
            }
        ],
        "connections": {},
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }


class TestCreateCommand:
    """Tests for create command."""

    def test_create_from_file_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_input: dict,
        sample_workflow_response: dict,
    ) -> None:
        """Test creating workflow from JSON file."""
        with cli_runner.isolated_filesystem():
            # Write workflow JSON to file
            with open("workflow.json", "w") as f:
                json.dump(sample_workflow_input, f)

            with (
                patch("n8n_cli.commands.create.require_config", return_value=mock_config),
                patch(
                    "n8n_cli.commands.create._create_workflow",
                    new_callable=AsyncMock,
                    return_value=sample_workflow_response,
                ),
            ):
                result = cli_runner.invoke(create, ["--file", "workflow.json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "123"
        assert output["name"] == "Test Workflow"

    def test_create_from_stdin_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_input: dict,
        sample_workflow_response: dict,
    ) -> None:
        """Test creating workflow from stdin."""
        with (
            patch("n8n_cli.commands.create.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.create._create_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow_response,
            ),
        ):
            result = cli_runner.invoke(
                create,
                ["--stdin"],
                input=json.dumps(sample_workflow_input),
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "123"

    def test_create_with_name_override(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_input: dict,
        sample_workflow_response: dict,
    ) -> None:
        """Test that --name overrides the name in JSON definition."""
        sample_workflow_response["name"] = "Overridden Name"

        with (
            patch("n8n_cli.commands.create.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.create._create_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow_response,
            ) as mock_create,
        ):
            result = cli_runner.invoke(
                create,
                ["--stdin", "--name", "Overridden Name"],
                input=json.dumps(sample_workflow_input),
            )

        assert result.exit_code == 0
        # Verify the workflow data passed to _create_workflow has overridden name
        call_args = mock_create.call_args
        workflow_data = call_args[0][2]  # Third positional arg is workflow_data
        assert workflow_data["name"] == "Overridden Name"

    def test_create_with_activate_flag(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_input: dict,
        sample_workflow_response: dict,
    ) -> None:
        """Test that --activate flag activates the workflow after creation."""
        activated_response = sample_workflow_response.copy()
        activated_response["active"] = True

        with (
            patch("n8n_cli.commands.create.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.create._create_workflow",
                new_callable=AsyncMock,
                return_value=activated_response,
            ) as mock_create,
        ):
            result = cli_runner.invoke(
                create,
                ["--stdin", "--activate"],
                input=json.dumps(sample_workflow_input),
            )

        assert result.exit_code == 0
        # Verify activate=True was passed
        call_args = mock_create.call_args
        assert call_args[0][3] is True  # Fourth positional arg is activate

    def test_create_returns_workflow_json_with_id(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_input: dict,
        sample_workflow_response: dict,
    ) -> None:
        """Test that output includes the created workflow with new ID."""
        with (
            patch("n8n_cli.commands.create.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.create._create_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow_response,
            ),
        ):
            result = cli_runner.invoke(
                create,
                ["--stdin"],
                input=json.dumps(sample_workflow_input),
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "id" in output
        assert output["id"] == "123"
        assert "createdAt" in output

    def test_create_invalid_json_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that invalid JSON returns clear error message."""
        with patch("n8n_cli.commands.create.require_config", return_value=mock_config):
            result = cli_runner.invoke(
                cli,
                ["create", "--stdin"],
                input="{ invalid json }",
            )

        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_create_missing_nodes_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that missing nodes field returns helpful error."""
        workflow_without_nodes = {"name": "Test"}

        with patch("n8n_cli.commands.create.require_config", return_value=mock_config):
            result = cli_runner.invoke(
                cli,
                ["create", "--stdin"],
                input=json.dumps(workflow_without_nodes),
            )

        assert result.exit_code == 1
        assert "missing required field 'nodes'" in result.output

    def test_create_missing_name_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that missing name (without --name flag) returns helpful error."""
        workflow_without_name = {"nodes": []}

        with patch("n8n_cli.commands.create.require_config", return_value=mock_config):
            result = cli_runner.invoke(
                cli,
                ["create", "--stdin"],
                input=json.dumps(workflow_without_name),
            )

        assert result.exit_code == 1
        assert "missing 'name'" in result.output
        assert "--name" in result.output

    def test_create_missing_name_with_override_succeeds(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_response: dict,
    ) -> None:
        """Test that --name flag allows creating workflow without name in JSON."""
        workflow_without_name = {"nodes": []}

        with (
            patch("n8n_cli.commands.create.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.create._create_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow_response,
            ),
        ):
            result = cli_runner.invoke(
                create,
                ["--stdin", "--name", "Provided Name"],
                input=json.dumps(workflow_without_name),
            )

        assert result.exit_code == 0

    def test_create_file_not_found_error(self, cli_runner: CliRunner) -> None:
        """Test that non-existent file returns error."""
        result = cli_runner.invoke(create, ["--file", "nonexistent.json"])

        assert result.exit_code != 0
        # Click handles this with its own error message

    def test_create_api_validation_error(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_input: dict,
    ) -> None:
        """Test that API validation errors (400) are handled properly."""
        from n8n_cli.exceptions import ValidationError

        with (
            patch("n8n_cli.commands.create.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.create._create_workflow",
                new_callable=AsyncMock,
                side_effect=ValidationError("Invalid node type"),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["create", "--stdin"],
                input=json.dumps(sample_workflow_input),
            )

        assert result.exit_code == 1
        assert "Invalid node type" in result.output

    def test_create_conflict_error(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_workflow_input: dict,
    ) -> None:
        """Test that 409 conflict error shows appropriate message."""
        from n8n_cli.exceptions import ApiError

        with (
            patch("n8n_cli.commands.create.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.create._create_workflow",
                new_callable=AsyncMock,
                side_effect=ApiError("Workflow already exists", 409),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["create", "--stdin"],
                input=json.dumps(sample_workflow_input),
            )

        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_create_requires_file_or_stdin(self, cli_runner: CliRunner) -> None:
        """Test that command fails when neither --file nor --stdin is provided."""
        result = cli_runner.invoke(cli, ["create"])

        assert result.exit_code == 1
        assert "Must specify either --file or --stdin" in result.output

    def test_create_file_stdin_mutually_exclusive(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --file and --stdin cannot be used together."""
        with cli_runner.isolated_filesystem():
            with open("workflow.json", "w") as f:
                f.write("{}")

            result = cli_runner.invoke(
                cli,
                ["create", "--file", "workflow.json", "--stdin"],
                input="{}",
            )

        assert result.exit_code == 1
        assert "Cannot use both --file and --stdin" in result.output

    def test_create_requires_configuration(self, cli_runner: CliRunner) -> None:
        """Test that create command fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        sample_input = {"name": "Test", "nodes": []}

        with patch(
            "n8n_cli.commands.create.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(
                cli,
                ["create", "--stdin"],
                input=json.dumps(sample_input),
            )

        assert result.exit_code == 2  # ConfigError uses exit code 2
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_create_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test create command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "create" in result.output

    def test_create_help_text(self, cli_runner: CliRunner) -> None:
        """Test create --help shows usage."""
        result = cli_runner.invoke(create, ["--help"])
        assert result.exit_code == 0
        assert "--file" in result.output
        assert "--stdin" in result.output
        assert "--name" in result.output
        assert "--activate" in result.output

    def test_create_json_must_be_object(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that JSON arrays or primitives are rejected."""
        with patch("n8n_cli.commands.create.require_config", return_value=mock_config):
            result = cli_runner.invoke(
                cli,
                ["create", "--stdin"],
                input="[1, 2, 3]",
            )

        assert result.exit_code == 1
        assert "must be an object" in result.output
