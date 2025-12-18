"""Tests for workflows command."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.workflows import workflows
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
def sample_workflows() -> list[dict[str, Any]]:
    """Provide sample workflow data."""
    return [
        {
            "id": "1",
            "name": "Workflow One",
            "active": True,
            "tags": [{"id": "t1", "name": "production"}],
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-02T00:00:00.000Z",
        },
        {
            "id": "2",
            "name": "Workflow Two",
            "active": False,
            "tags": [{"id": "t2", "name": "development"}],
            "createdAt": "2024-01-03T00:00:00.000Z",
            "updatedAt": "2024-01-04T00:00:00.000Z",
        },
        {
            "id": "3",
            "name": "Workflow Three",
            "active": True,
            "tags": [],
            "createdAt": "2024-01-05T00:00:00.000Z",
            "updatedAt": "2024-01-06T00:00:00.000Z",
        },
    ]


class TestWorkflowsCommand:
    """Tests for workflows command."""

    def test_workflows_returns_all_workflows(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflows: list[dict]
    ) -> None:
        """Test that workflows command returns all workflows as JSON."""
        with (
            patch("n8n_cli.commands.workflows.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflows._fetch_workflows",
                new_callable=AsyncMock,
                return_value=sample_workflows,
            ),
        ):
            result = cli_runner.invoke(workflows)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 3
        assert output[0]["name"] == "Workflow One"

    def test_workflows_active_flag_filters(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflows: list[dict]
    ) -> None:
        """Test --active flag filters to active workflows only."""
        active_workflows = [w for w in sample_workflows if w["active"]]

        with (
            patch("n8n_cli.commands.workflows.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflows._fetch_workflows",
                new_callable=AsyncMock,
                return_value=active_workflows,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(workflows, ["--active"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[0][2] is True  # active parameter

    def test_workflows_inactive_flag_filters(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflows: list[dict]
    ) -> None:
        """Test --inactive flag filters to inactive workflows only."""
        inactive_workflows = [w for w in sample_workflows if not w["active"]]

        with (
            patch("n8n_cli.commands.workflows.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflows._fetch_workflows",
                new_callable=AsyncMock,
                return_value=inactive_workflows,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(workflows, ["--inactive"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[0][2] is False  # active parameter

    def test_workflows_active_and_inactive_mutually_exclusive(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that --active and --inactive cannot be used together."""
        with patch("n8n_cli.commands.workflows.require_config", return_value=mock_config):
            result = cli_runner.invoke(workflows, ["--active", "--inactive"])

        assert result.exit_code == 1
        assert "Cannot use both --active and --inactive" in result.output

    def test_workflows_tag_filter(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflows: list[dict]
    ) -> None:
        """Test --tag flag filters by tag name."""
        tagged_workflows = [
            w for w in sample_workflows
            if any(t["name"] == "production" for t in w.get("tags", []))
        ]

        with (
            patch("n8n_cli.commands.workflows.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflows._fetch_workflows",
                new_callable=AsyncMock,
                return_value=tagged_workflows,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(workflows, ["--tag", "production"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[0][3] == ["production"]  # tags parameter

    def test_workflows_multiple_tags(
        self, cli_runner: CliRunner, mock_config: Config, sample_workflows: list[dict]
    ) -> None:
        """Test multiple --tag flags work together."""
        with (
            patch("n8n_cli.commands.workflows.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflows._fetch_workflows",
                new_callable=AsyncMock,
                return_value=sample_workflows[:2],
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(
                workflows, ["--tag", "production", "--tag", "development"]
            )

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[0][3] == ["production", "development"]

    def test_workflows_empty_list_returns_empty_array(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test empty workflow list returns empty JSON array."""
        with (
            patch("n8n_cli.commands.workflows.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.workflows._fetch_workflows",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = cli_runner.invoke(workflows)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output == []

    def test_workflows_requires_configuration(self, cli_runner: CliRunner) -> None:
        """Test that workflows command fails when not configured."""
        from n8n_cli.config import ConfigurationError

        with patch(
            "n8n_cli.commands.workflows.require_config",
            side_effect=ConfigurationError("Not configured"),
        ):
            result = cli_runner.invoke(workflows)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_workflows_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test workflows command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "workflows" in result.output

    def test_workflows_help_text(self, cli_runner: CliRunner) -> None:
        """Test workflows --help shows all options."""
        result = cli_runner.invoke(workflows, ["--help"])
        assert result.exit_code == 0
        assert "--active" in result.output
        assert "--inactive" in result.output
        assert "--tag" in result.output


class TestGetWorkflowsClient:
    """Tests for N8nClient.get_workflows method."""

    @pytest.mark.asyncio
    async def test_get_workflows_returns_all(
        self, sample_workflows: list[dict]
    ) -> None:
        """Test get_workflows returns all workflows by default."""
        from unittest.mock import MagicMock

        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_workflows}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_workflows()

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_workflows_filters_active(
        self, sample_workflows: list[dict]
    ) -> None:
        """Test get_workflows filters by active status."""
        from unittest.mock import MagicMock

        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_workflows}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_workflows(active=True)

        assert len(result) == 2
        assert all(w["active"] for w in result)

    @pytest.mark.asyncio
    async def test_get_workflows_filters_inactive(
        self, sample_workflows: list[dict]
    ) -> None:
        """Test get_workflows filters to inactive workflows."""
        from unittest.mock import MagicMock

        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_workflows}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_workflows(active=False)

        assert len(result) == 1
        assert not result[0]["active"]

    @pytest.mark.asyncio
    async def test_get_workflows_filters_by_tags(
        self, sample_workflows: list[dict]
    ) -> None:
        """Test get_workflows filters by tag names."""
        from unittest.mock import MagicMock

        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_workflows}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_workflows(tags=["production"])

        assert len(result) == 1
        assert result[0]["name"] == "Workflow One"
