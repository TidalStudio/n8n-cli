"""Tests for workflow command."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from click.testing import CliRunner

from n8n_cli.commands.workflow import workflow
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
    """Provide sample workflow data with full details."""
    return {
        "id": "1",
        "name": "My Test Workflow",
        "active": True,
        "nodes": [
            {
                "id": "node1",
                "name": "Start",
                "type": "n8n-nodes-base.start",
                "position": [250, 300],
                "parameters": {},
            },
            {
                "id": "node2",
                "name": "HTTP Request",
                "type": "n8n-nodes-base.httpRequest",
                "position": [450, 300],
                "parameters": {"url": "https://api.example.com"},
            },
        ],
        "connections": {
            "Start": {
                "main": [[{"node": "HTTP Request", "type": "main", "index": 0}]]
            }
        },
        "settings": {"executionOrder": "v1"},
        "tags": [{"id": "t1", "name": "production"}],
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-02T00:00:00.000Z",
    }


class TestWorkflowCommand:
    """Tests for workflow command."""

    def test_workflow_returns_full_workflow(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflow: dict
    ) -> None:
        """Test that workflow command returns full workflow JSON."""
        with (
            patch("n8n_cli.commands.workflow.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflow._fetch_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow,
            ),
        ):
            result = cli_runner.invoke(workflow, ["1"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "1"
        assert output["name"] == "My Test Workflow"
        assert "nodes" in output
        assert "connections" in output
        assert "settings" in output

    def test_workflow_with_string_id(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflow: dict
    ) -> None:
        """Test workflow command works with string IDs."""
        sample_workflow["id"] = "abc123"

        with (
            patch("n8n_cli.commands.workflow.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflow._fetch_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(workflow, ["abc123"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][2] == "abc123"

    def test_workflow_not_found_returns_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that 404 response returns clear error message."""
        mock_response = httpx.Response(404, request=httpx.Request("GET", "http://test"))
        error = httpx.HTTPStatusError("Not found", request=mock_response.request, response=mock_response)

        with (
            patch("n8n_cli.commands.workflow.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflow._fetch_workflow",
                new_callable=AsyncMock,
                side_effect=error,
            ),
        ):
            result = cli_runner.invoke(workflow, ["999"])

        assert result.exit_code == 1
        assert "Workflow not found: 999" in result.output

    def test_workflow_api_error_returns_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that API errors return status code."""
        mock_response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
        error = httpx.HTTPStatusError("Server error", request=mock_response.request, response=mock_response)

        with (
            patch("n8n_cli.commands.workflow.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflow._fetch_workflow",
                new_callable=AsyncMock,
                side_effect=error,
            ),
        ):
            result = cli_runner.invoke(workflow, ["1"])

        assert result.exit_code == 1
        assert "API error: 500" in result.output

    def test_workflow_requires_configuration(self, cli_runner: CliRunner) -> None:
        """Test that workflow command fails when not configured."""
        from n8n_cli.config import ConfigurationError

        with patch(
            "n8n_cli.commands.workflow.require_config",
            side_effect=ConfigurationError("Not configured"),
        ):
            result = cli_runner.invoke(workflow, ["1"])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_workflow_requires_id_argument(self, cli_runner: CliRunner) -> None:
        """Test that workflow command requires workflow_id argument."""
        result = cli_runner.invoke(workflow, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_workflow_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test workflow command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "workflow" in result.output

    def test_workflow_help_text(self, cli_runner: CliRunner) -> None:
        """Test workflow --help shows usage."""
        result = cli_runner.invoke(workflow, ["--help"])
        assert result.exit_code == 0
        assert "WORKFLOW_ID" in result.output
        assert "detailed information" in result.output.lower()
