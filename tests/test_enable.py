"""Tests for enable command."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.enable import enable
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
def inactive_workflow() -> dict[str, Any]:
    """Provide sample inactive workflow data."""
    return {
        "id": "123",
        "name": "My Test Workflow",
        "active": False,
        "nodes": [],
        "connections": {},
    }


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


class TestEnableCommand:
    """Tests for enable command."""

    def test_enable_success(
        self, cli_runner: CliRunner, mock_config: Config, active_workflow: dict
    ) -> None:
        """Test that enable command succeeds and outputs JSON."""
        with (
            patch("n8n_cli.commands.enable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.enable._enable_workflow",
                new_callable=AsyncMock,
                return_value=active_workflow,
            ) as mock_enable,
        ):
            result = cli_runner.invoke(enable, ["123"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "123"
        assert output["active"] is True
        mock_enable.assert_called_once_with(
            api_url="http://localhost:5678",
            api_key="test-api-key",
            workflow_id="123",
        )

    def test_enable_already_active_idempotent(
        self, cli_runner: CliRunner, mock_config: Config, active_workflow: dict
    ) -> None:
        """Test that enabling an already-active workflow succeeds (idempotent)."""
        with (
            patch("n8n_cli.commands.enable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.enable._enable_workflow",
                new_callable=AsyncMock,
                return_value=active_workflow,
            ),
        ):
            result = cli_runner.invoke(enable, ["123"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["active"] is True

    def test_enable_not_found_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that 404 response returns clear error message."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch("n8n_cli.commands.enable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.enable._enable_workflow",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Workflow not found: 999"),
            ),
        ):
            result = cli_runner.invoke(cli, ["enable", "999"])

        assert result.exit_code == 1
        assert "Workflow not found: 999" in result.output

    def test_enable_workflow_with_errors(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that 400 response shows error message from API."""
        from n8n_cli.exceptions import ValidationError

        with (
            patch("n8n_cli.commands.enable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.enable._enable_workflow",
                new_callable=AsyncMock,
                side_effect=ValidationError("Workflow has validation errors"),
            ),
        ):
            result = cli_runner.invoke(cli, ["enable", "123"])

        assert result.exit_code == 1
        assert "Workflow has validation errors" in result.output

    def test_enable_api_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that API errors return status code."""
        from n8n_cli.exceptions import ApiError

        with (
            patch("n8n_cli.commands.enable.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.enable._enable_workflow",
                new_callable=AsyncMock,
                side_effect=ApiError("API error (500): Server error", 500),
            ),
        ):
            result = cli_runner.invoke(cli, ["enable", "123"])

        assert result.exit_code == 1
        assert "500" in result.output

    def test_enable_config_error(self, cli_runner: CliRunner) -> None:
        """Test that enable command fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.enable.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(cli, ["enable", "123"])

        assert result.exit_code == 2  # ConfigError uses exit code 2
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_enable_requires_id_argument(self, cli_runner: CliRunner) -> None:
        """Test that enable command requires workflow_id argument."""
        result = cli_runner.invoke(enable, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_enable_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test enable command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "enable" in result.output

    def test_enable_help_text(self, cli_runner: CliRunner) -> None:
        """Test enable --help shows usage."""
        result = cli_runner.invoke(enable, ["--help"])
        assert result.exit_code == 0
        assert "WORKFLOW_ID" in result.output
        assert "activate" in result.output.lower()
