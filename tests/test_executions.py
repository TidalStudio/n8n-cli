"""Tests for executions command."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.executions import executions
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
def sample_executions() -> list[dict[str, Any]]:
    """Provide sample execution data."""
    return [
        {
            "id": "101",
            "workflowId": "1",
            "status": "success",
            "startedAt": "2025-12-18T10:00:00.000Z",
            "stoppedAt": "2025-12-18T10:00:05.000Z",
        },
        {
            "id": "102",
            "workflowId": "1",
            "status": "error",
            "startedAt": "2025-12-18T11:00:00.000Z",
            "stoppedAt": "2025-12-18T11:00:03.000Z",
        },
        {
            "id": "103",
            "workflowId": "2",
            "status": "running",
            "startedAt": "2025-12-18T12:00:00.000Z",
            "stoppedAt": None,
        },
    ]


class TestExecutionsCommand:
    """Tests for executions command."""

    def test_executions_returns_all_executions(
        self, cli_runner: CliRunner, mock_config: Config, sample_executions: list[dict]
    ) -> None:
        """Test that executions command returns all executions as JSON."""
        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=sample_executions,
            ),
        ):
            result = cli_runner.invoke(executions)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 3
        assert output[0]["id"] == "101"
        assert output[0]["status"] == "success"

    def test_executions_workflow_filter(
        self, cli_runner: CliRunner, mock_config: Config, sample_executions: list[dict]
    ) -> None:
        """Test --workflow flag filters by workflow ID."""
        filtered = [e for e in sample_executions if e["workflowId"] == "1"]

        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=filtered,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(executions, ["--workflow", "1"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[2] == "1"  # workflow_id parameter

    def test_executions_status_filter(
        self, cli_runner: CliRunner, mock_config: Config, sample_executions: list[dict]
    ) -> None:
        """Test --status flag filters by execution status."""
        success_executions = [e for e in sample_executions if e["status"] == "success"]

        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=success_executions,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(executions, ["--status", "success"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[3] == "success"  # status parameter

    def test_executions_status_case_insensitive(
        self, cli_runner: CliRunner, mock_config: Config, sample_executions: list[dict]
    ) -> None:
        """Test --status flag is case insensitive."""
        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=[sample_executions[0]],
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(executions, ["--status", "SUCCESS"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()

    def test_executions_invalid_status_rejected(
        self, cli_runner: CliRunner
    ) -> None:
        """Test invalid status value is rejected by Click."""
        result = cli_runner.invoke(executions, ["--status", "invalid"])
        assert result.exit_code == 2
        assert "Invalid value for '--status'" in result.output

    def test_executions_limit_option(
        self, cli_runner: CliRunner, mock_config: Config, sample_executions: list[dict]
    ) -> None:
        """Test --limit option is passed correctly."""
        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=sample_executions[:1],
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(executions, ["--limit", "1"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[4] == 1  # limit parameter

    def test_executions_default_limit(
        self, cli_runner: CliRunner, mock_config: Config, sample_executions: list[dict]
    ) -> None:
        """Test default limit is 20."""
        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=sample_executions,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(executions)

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[4] == 20  # default limit

    def test_executions_empty_list_returns_empty_array(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test empty execution list returns empty JSON array."""
        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = cli_runner.invoke(executions)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output == []

    def test_executions_requires_configuration(self, cli_runner: CliRunner) -> None:
        """Test that executions command fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.executions.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(cli, ["executions"])

        assert result.exit_code == 2  # ConfigError uses exit code 2
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_executions_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test executions command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "executions" in result.output

    def test_executions_help_text(self, cli_runner: CliRunner) -> None:
        """Test executions --help shows all options."""
        result = cli_runner.invoke(executions, ["--help"])
        assert result.exit_code == 0
        assert "--workflow" in result.output
        assert "--status" in result.output
        assert "--limit" in result.output

    def test_executions_combined_filters(
        self, cli_runner: CliRunner, mock_config: Config, sample_executions: list[dict]
    ) -> None:
        """Test multiple filters can be combined."""
        with (
            patch(
                "n8n_cli.commands.executions.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.executions._fetch_executions",
                new_callable=AsyncMock,
                return_value=[sample_executions[0]],
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(
                executions, ["--workflow", "1", "--status", "success", "--limit", "10"]
            )

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[2] == "1"  # workflow_id
        assert call_args[3] == "success"  # status
        assert call_args[4] == 10  # limit


class TestGetExecutionsClient:
    """Tests for N8nClient.get_executions method."""

    @pytest.mark.asyncio
    async def test_get_executions_returns_all(
        self, sample_executions: list[dict]
    ) -> None:
        """Test get_executions returns executions from API."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_executions}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_get = AsyncMock(return_value=mock_response)
            client._client.get = mock_get
            result = await client.get_executions()

            assert len(result) == 3
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"]["limit"] == 20
            assert call_kwargs[1]["params"]["includeData"] == "false"

    @pytest.mark.asyncio
    async def test_get_executions_with_workflow_filter(
        self, sample_executions: list[dict]
    ) -> None:
        """Test get_executions passes workflow filter to API."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_executions}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_get = AsyncMock(return_value=mock_response)
            client._client.get = mock_get
            await client.get_executions(workflow_id="123")

            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"]["workflowId"] == "123"

    @pytest.mark.asyncio
    async def test_get_executions_with_status_filter(
        self, sample_executions: list[dict]
    ) -> None:
        """Test get_executions passes status filter to API."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_executions}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_get = AsyncMock(return_value=mock_response)
            client._client.get = mock_get
            await client.get_executions(status="error")

            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_get_executions_respects_limit(
        self, sample_executions: list[dict]
    ) -> None:
        """Test get_executions passes limit to API."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_executions}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_get = AsyncMock(return_value=mock_response)
            client._client.get = mock_get
            await client.get_executions(limit=50)

            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_get_executions_caps_limit_at_250(
        self, sample_executions: list[dict]
    ) -> None:
        """Test get_executions caps limit at API maximum of 250."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_executions}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_get = AsyncMock(return_value=mock_response)
            client._client.get = mock_get
            await client.get_executions(limit=500)

            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"]["limit"] == 250

    @pytest.mark.asyncio
    async def test_get_executions_empty_response(self) -> None:
        """Test get_executions handles empty response."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_executions()

            assert result == []
