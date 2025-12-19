"""Tests for disable command."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.disable import disable
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
def active_workflow() -> dict[str, Any]:
    """Provide sample active workflow data."""
    return {
        "id": "123",
        "name": "My Test Workflow",
        "active": True,
        "nodes": [],
        "connections": {},
    }


@pytest.fixture
def inactive_workflow() -> dict[str, Any]:
    """Provide sample inactive workflow data."""
    return {
        "id": "123",
        "name": "My Test Workflow",
        "active": False,
        "nodes": [],
        "connections": {},
    }


class TestDisableCommand:
    """Tests for disable command."""

    def test_disable_success(
        self, cli_runner: CliRunner, mock_config: Config, inactive_workflow: dict
    ) -> None:
        """Test that disable command succeeds and outputs JSON."""
        with (
            patch("n8n_cli.commands.disable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.disable._disable_workflow",
                new_callable=AsyncMock,
                return_value=inactive_workflow,
            ) as mock_disable,
        ):
            result = cli_runner.invoke(disable, ["123"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "123"
        assert output["active"] is False
        mock_disable.assert_called_once_with(
            api_url="http://localhost:5678",
            api_key="test-api-key",
            workflow_id="123",
        )

    def test_disable_already_inactive_idempotent(
        self, cli_runner: CliRunner, mock_config: Config, inactive_workflow: dict
    ) -> None:
        """Test that disabling an already-inactive workflow succeeds (idempotent)."""
        with (
            patch("n8n_cli.commands.disable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.disable._disable_workflow",
                new_callable=AsyncMock,
                return_value=inactive_workflow,
            ),
        ):
            result = cli_runner.invoke(disable, ["123"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["active"] is False

    def test_disable_not_found_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that 404 response returns clear error message."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch("n8n_cli.commands.disable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.disable._disable_workflow",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Workflow not found: 999"),
            ),
        ):
            result = cli_runner.invoke(cli, ["disable", "999"])

        assert result.exit_code == 1
        assert "Workflow not found: 999" in result.output

    def test_disable_api_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that API errors return status code."""
        from n8n_cli.exceptions import ApiError

        with (
            patch("n8n_cli.commands.disable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.disable._disable_workflow",
                new_callable=AsyncMock,
                side_effect=ApiError("API error (500): Server error", 500),
            ),
        ):
            result = cli_runner.invoke(cli, ["disable", "123"])

        assert result.exit_code == 1
        assert "500" in result.output

    def test_disable_config_error(self, cli_runner: CliRunner) -> None:
        """Test that disable command fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.disable.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(cli, ["disable", "123"])

        assert result.exit_code == 2  # ConfigError uses exit code 2
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_disable_requires_id_argument(self, cli_runner: CliRunner) -> None:
        """Test that disable command requires workflow_id argument."""
        result = cli_runner.invoke(disable, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_disable_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test disable command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "disable" in result.output

    def test_disable_help_text(self, cli_runner: CliRunner) -> None:
        """Test disable --help shows usage."""
        result = cli_runner.invoke(disable, ["--help"])
        assert result.exit_code == 0
        assert "WORKFLOW_ID" in result.output
        assert "deactivate" in result.output.lower()
