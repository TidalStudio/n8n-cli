"""Tests for delete command."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.delete import delete
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
    """Provide sample workflow data."""
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
        "id": "456",
        "name": "Active Workflow",
        "active": True,
        "nodes": [],
        "connections": {},
    }


class TestDeleteCommand:
    """Tests for delete command."""

    def test_delete_without_confirm_shows_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that delete without --confirm shows error."""
        with patch("n8n_cli.commands.delete.require_config", return_value=mock_config):
            result = cli_runner.invoke(cli, ["delete", "123"])

        assert result.exit_code == 1
        assert "Deletion requires confirmation" in result.output
        assert "--confirm" in result.output

    def test_delete_with_confirm_succeeds(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflow: dict
    ) -> None:
        """Test that delete with --confirm succeeds."""
        with (
            patch("n8n_cli.commands.delete.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.delete._get_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow,
            ),
            patch(
                "n8n_cli.commands.delete._delete_workflow",
                new_callable=AsyncMock,
            ) as mock_delete,
        ):
            result = cli_runner.invoke(delete, ["123", "--confirm"])

        assert result.exit_code == 0
        assert "Deleted workflow 'My Test Workflow'" in result.output
        assert "ID: 123" in result.output
        mock_delete.assert_called_once()

    def test_delete_with_force_succeeds(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflow: dict
    ) -> None:
        """Test that delete with --force succeeds."""
        with (
            patch("n8n_cli.commands.delete.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.delete._get_workflow",
                new_callable=AsyncMock,
                return_value=sample_workflow,
            ),
            patch(
                "n8n_cli.commands.delete._delete_workflow",
                new_callable=AsyncMock,
            ) as mock_delete,
        ):
            result = cli_runner.invoke(delete, ["123", "--force"])

        assert result.exit_code == 0
        assert "Deleted workflow" in result.output
        mock_delete.assert_called_once()

    def test_delete_active_workflow_warns(
        self, cli_runner: CliRunner, mock_config: Config, active_workflow: dict
    ) -> None:
        """Test that deleting active workflow with --confirm shows warning."""
        with (
            patch("n8n_cli.commands.delete.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.delete._get_workflow",
                new_callable=AsyncMock,
                return_value=active_workflow,
            ),
        ):
            result = cli_runner.invoke(cli, ["delete", "456", "--confirm"])

        assert result.exit_code == 1
        assert "currently active" in result.output
        assert "--force" in result.output

    def test_delete_active_workflow_force_allows(
        self, cli_runner: CliRunner, mock_config: Config, active_workflow: dict
    ) -> None:
        """Test that deleting active workflow with --force succeeds."""
        with (
            patch("n8n_cli.commands.delete.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.delete._get_workflow",
                new_callable=AsyncMock,
                return_value=active_workflow,
            ),
            patch(
                "n8n_cli.commands.delete._delete_workflow",
                new_callable=AsyncMock,
            ) as mock_delete,
        ):
            result = cli_runner.invoke(delete, ["456", "--force"])

        assert result.exit_code == 0
        assert "Deleted workflow 'Active Workflow'" in result.output
        mock_delete.assert_called_once()

    def test_delete_not_found_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that 404 response returns clear error message."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch("n8n_cli.commands.delete.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.delete._get_workflow",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Workflow not found: 999"),
            ),
        ):
            result = cli_runner.invoke(cli, ["delete", "999", "--confirm"])

        assert result.exit_code == 1
        assert "Workflow not found: 999" in result.output

    def test_delete_api_error(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that API errors return status code."""
        from n8n_cli.exceptions import ApiError

        with (
            patch("n8n_cli.commands.delete.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.delete._get_workflow",
                new_callable=AsyncMock,
                side_effect=ApiError("API error (500): Server error", 500),
            ),
        ):
            result = cli_runner.invoke(cli, ["delete", "123", "--confirm"])

        assert result.exit_code == 1
        assert "500" in result.output

    def test_delete_config_error(self, cli_runner: CliRunner) -> None:
        """Test that delete command fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.delete.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(cli, ["delete", "123", "--confirm"])

        assert result.exit_code == 2  # ConfigError uses exit code 2
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_delete_requires_id_argument(self, cli_runner: CliRunner) -> None:
        """Test that delete command requires workflow_id argument."""
        result = cli_runner.invoke(delete, ["--confirm"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_delete_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test delete command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "delete" in result.output

    def test_delete_help_text(self, cli_runner: CliRunner) -> None:
        """Test delete --help shows usage."""
        result = cli_runner.invoke(delete, ["--help"])
        assert result.exit_code == 0
        assert "WORKFLOW_ID" in result.output
        assert "--confirm" in result.output
        assert "--force" in result.output
