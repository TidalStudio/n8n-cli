"""Tests for trigger command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from click.testing import CliRunner

from n8n_cli.commands.trigger import trigger
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
def execution_response() -> dict[str, Any]:
    """Provide sample execution response."""
    return {"executionId": "12345"}


@pytest.fixture
def completed_execution() -> dict[str, Any]:
    """Provide sample completed execution."""
    return {
        "id": "12345",
        "status": "success",
        "data": {"resultData": {"runData": {}}},
    }


@pytest.fixture
def failed_execution() -> dict[str, Any]:
    """Provide sample failed execution."""
    return {
        "id": "12345",
        "status": "error",
        "data": {"resultData": {"error": {"message": "Something went wrong"}}},
    }


class TestTriggerCommand:
    """Tests for trigger command."""

    def test_trigger_simple_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        execution_response: dict,
    ) -> None:
        """Test simple trigger without data returns execution ID."""
        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                return_value=execution_response,
            ) as mock_trigger,
        ):
            result = cli_runner.invoke(trigger, ["123"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["executionId"] == "12345"
        mock_trigger.assert_called_once()

    def test_trigger_with_data_json(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        execution_response: dict,
    ) -> None:
        """Test trigger with --data passes input data."""
        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                return_value=execution_response,
            ) as mock_trigger,
        ):
            result = cli_runner.invoke(
                trigger, ["123", "--data", '{"key": "value"}']
            )

        assert result.exit_code == 0
        # Check that the data was passed
        call_args = mock_trigger.call_args
        assert call_args[0][3] == {"key": "value"}  # 4th positional arg is data

    def test_trigger_with_file_input(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        execution_response: dict,
        tmp_path: Path,
    ) -> None:
        """Test trigger with --file reads input from file."""
        input_file = tmp_path / "input.json"
        input_file.write_text('{"fromFile": true}')

        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                return_value=execution_response,
            ) as mock_trigger,
        ):
            result = cli_runner.invoke(trigger, ["123", "--file", str(input_file)])

        assert result.exit_code == 0
        call_args = mock_trigger.call_args
        assert call_args[0][3] == {"fromFile": True}

    def test_trigger_data_and_file_mutually_exclusive(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that --data and --file cannot be used together."""
        input_file = tmp_path / "input.json"
        input_file.write_text('{"key": "value"}')

        with patch("n8n_cli.commands.trigger.require_config", return_value=mock_config):
            result = cli_runner.invoke(
                trigger, ["123", "--data", '{"key": "value"}', "--file", str(input_file)]
            )

        assert result.exit_code == 1
        assert "Cannot use both --data and --file" in result.output

    def test_trigger_invalid_json_data(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that invalid JSON in --data returns clear error."""
        with patch("n8n_cli.commands.trigger.require_config", return_value=mock_config):
            result = cli_runner.invoke(trigger, ["123", "--data", "not valid json"])

        assert result.exit_code == 1
        assert "Invalid JSON data" in result.output

    def test_trigger_json_data_must_be_object(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that --data must be a JSON object, not array or primitive."""
        with patch("n8n_cli.commands.trigger.require_config", return_value=mock_config):
            result = cli_runner.invoke(trigger, ["123", "--data", '["array"]'])

        assert result.exit_code == 1
        assert "must be an object" in result.output

    def test_trigger_invalid_json_file(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that invalid JSON in file returns clear error."""
        input_file = tmp_path / "invalid.json"
        input_file.write_text("not valid json")

        with patch("n8n_cli.commands.trigger.require_config", return_value=mock_config):
            result = cli_runner.invoke(trigger, ["123", "--file", str(input_file)])

        assert result.exit_code == 1
        assert "Invalid JSON in file" in result.output

    def test_trigger_workflow_not_found(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that 404 response returns workflow not found error."""
        mock_response = httpx.Response(404, request=httpx.Request("POST", "http://test"))
        error = httpx.HTTPStatusError(
            "Not found", request=mock_response.request, response=mock_response
        )

        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                side_effect=error,
            ),
        ):
            result = cli_runner.invoke(trigger, ["999"])

        assert result.exit_code == 1
        assert "Workflow not found: 999" in result.output

    def test_trigger_workflow_inactive(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that inactive workflow returns helpful error."""
        mock_response = httpx.Response(
            400,
            request=httpx.Request("POST", "http://test"),
            json={"message": "Workflow is not active"},
        )
        error = httpx.HTTPStatusError(
            "Bad request", request=mock_response.request, response=mock_response
        )

        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                side_effect=error,
            ),
        ):
            result = cli_runner.invoke(trigger, ["123"])

        assert result.exit_code == 1
        assert "not active" in result.output
        assert "n8n-cli update 123 --activate" in result.output

    def test_trigger_api_error(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that API errors return status code."""
        mock_response = httpx.Response(500, request=httpx.Request("POST", "http://test"))
        error = httpx.HTTPStatusError(
            "Server error", request=mock_response.request, response=mock_response
        )

        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                side_effect=error,
            ),
        ):
            result = cli_runner.invoke(trigger, ["123"])

        assert result.exit_code == 1
        assert "API error: 500" in result.output

    def test_trigger_config_error(self, cli_runner: CliRunner) -> None:
        """Test that trigger command fails when not configured."""
        from n8n_cli.config import ConfigurationError

        with patch(
            "n8n_cli.commands.trigger.require_config",
            side_effect=ConfigurationError("Not configured"),
        ):
            result = cli_runner.invoke(trigger, ["123"])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Not configured" in result.output

    def test_trigger_requires_id_argument(self, cli_runner: CliRunner) -> None:
        """Test that trigger command requires workflow_id argument."""
        result = cli_runner.invoke(trigger, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_trigger_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test trigger command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "trigger" in result.output

    def test_trigger_help_text(self, cli_runner: CliRunner) -> None:
        """Test trigger --help shows usage."""
        result = cli_runner.invoke(trigger, ["--help"])
        assert result.exit_code == 0
        assert "WORKFLOW_ID" in result.output
        assert "--data" in result.output
        assert "--file" in result.output
        assert "--wait" in result.output
        assert "--timeout" in result.output

    def test_trigger_with_wait_returns_full_execution(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        completed_execution: dict,
    ) -> None:
        """Test trigger with --wait returns full execution result."""
        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                return_value=completed_execution,
            ),
        ):
            result = cli_runner.invoke(trigger, ["123", "--wait"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["status"] == "success"
        assert output["id"] == "12345"

    def test_trigger_timeout_error(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
    ) -> None:
        """Test that timeout returns error."""
        with (
            patch("n8n_cli.commands.trigger.require_config", return_value=mock_config),
            patch(
                "n8n_cli.commands.trigger._trigger_workflow",
                new_callable=AsyncMock,
                side_effect=TimeoutError("Execution did not complete"),
            ),
        ):
            result = cli_runner.invoke(trigger, ["123", "--wait", "--timeout", "5"])

        assert result.exit_code == 1
        assert "timed out" in result.output

    def test_trigger_default_timeout(self, cli_runner: CliRunner) -> None:
        """Test that default timeout is 300 seconds."""
        result = cli_runner.invoke(trigger, ["--help"])
        assert "default: 300" in result.output


class TestTriggerWorkflowFunction:
    """Tests for the _trigger_workflow async function."""

    @pytest.mark.asyncio
    async def test_execute_without_wait(self) -> None:
        """Test execution without wait returns immediately."""
        from n8n_cli.commands.trigger import _trigger_workflow

        with patch("n8n_cli.commands.trigger.N8nClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.execute_workflow.return_value = {
                "executionId": "12345"
            }
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await _trigger_workflow(
                api_url="http://localhost:5678",
                api_key="test-key",
                workflow_id="123",
                data=None,
                wait_for_completion=False,
                timeout=300,
            )

        assert result["executionId"] == "12345"

    @pytest.mark.asyncio
    async def test_execute_with_wait_polls_until_complete(self) -> None:
        """Test execution with wait polls until terminal status."""
        from n8n_cli.commands.trigger import _trigger_workflow

        with patch("n8n_cli.commands.trigger.N8nClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.execute_workflow.return_value = {"executionId": "12345"}
            mock_client.get_execution.side_effect = [
                {"id": "12345", "status": "running"},
                {"id": "12345", "status": "running"},
                {"id": "12345", "status": "success", "data": {}},
            ]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("n8n_cli.commands.trigger.asyncio.sleep", new_callable=AsyncMock):
                result = await _trigger_workflow(
                    api_url="http://localhost:5678",
                    api_key="test-key",
                    workflow_id="123",
                    data=None,
                    wait_for_completion=True,
                    timeout=300,
                )

        assert result["status"] == "success"
        assert mock_client.get_execution.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_data_passes_input_data(self) -> None:
        """Test that input data is passed to execute_workflow."""
        from n8n_cli.commands.trigger import _trigger_workflow

        with patch("n8n_cli.commands.trigger.N8nClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.execute_workflow.return_value = {"executionId": "12345"}
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await _trigger_workflow(
                api_url="http://localhost:5678",
                api_key="test-key",
                workflow_id="123",
                data={"key": "value"},
                wait_for_completion=False,
                timeout=300,
            )

        mock_client.execute_workflow.assert_called_once_with("123", {"key": "value"})
