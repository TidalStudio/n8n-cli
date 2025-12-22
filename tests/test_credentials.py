"""Tests for credentials commands."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.credentials import credentials
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
def sample_credential_input() -> dict[str, Any]:
    """Provide sample credential input data."""
    return {
        "user": "admin",
        "password": "secret123",
    }


@pytest.fixture
def sample_credential_response() -> dict[str, Any]:
    """Provide sample credential response from API."""
    return {
        "id": "123",
        "name": "New Credential",
        "type": "httpBasicAuth",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }


@pytest.fixture
def sample_schema_response() -> dict[str, Any]:
    """Provide sample credential schema response."""
    return {
        "additionalProperties": False,
        "type": "object",
        "properties": {
            "user": {"type": "string"},
            "password": {"type": "string"},
        },
        "required": ["user", "password"],
    }


class TestCredentialsCreate:
    """Tests for credentials create command."""

    def test_credentials_create_from_file_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_credential_input: dict,
        sample_credential_response: dict,
    ) -> None:
        """Test creating credential from JSON file."""
        with cli_runner.isolated_filesystem():
            with open("cred.json", "w") as f:
                json.dump(sample_credential_input, f)

            with (
                patch(
                    "n8n_cli.commands.credentials.require_config",
                    return_value=mock_config,
                ),
                patch(
                    "n8n_cli.commands.credentials._create_credential",
                    new_callable=AsyncMock,
                    return_value=sample_credential_response,
                ),
            ):
                result = cli_runner.invoke(
                    credentials,
                    [
                        "create",
                        "--type",
                        "httpBasicAuth",
                        "--name",
                        "New Credential",
                        "--file",
                        "cred.json",
                    ],
                )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "123"
        assert output["name"] == "New Credential"

    def test_credentials_create_from_stdin_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_credential_input: dict,
        sample_credential_response: dict,
    ) -> None:
        """Test creating credential from stdin."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._create_credential",
                new_callable=AsyncMock,
                return_value=sample_credential_response,
            ),
        ):
            result = cli_runner.invoke(
                credentials,
                [
                    "create",
                    "--type",
                    "httpBasicAuth",
                    "--name",
                    "New Credential",
                    "--stdin",
                ],
                input=json.dumps(sample_credential_input),
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "123"

    def test_credentials_create_invalid_json(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that invalid JSON returns clear error message."""
        with patch(
            "n8n_cli.commands.credentials.require_config", return_value=mock_config
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "credentials",
                    "create",
                    "--type",
                    "httpBasicAuth",
                    "--name",
                    "Test",
                    "--stdin",
                ],
                input="{ invalid json }",
            )

        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_credentials_create_no_input_error(self, cli_runner: CliRunner) -> None:
        """Test that command fails when neither --file nor --stdin is provided."""
        result = cli_runner.invoke(
            cli,
            ["credentials", "create", "--type", "httpBasicAuth", "--name", "Test"],
        )

        assert result.exit_code == 1
        assert "Must specify either --file or --stdin" in result.output

    def test_credentials_create_both_options_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --file and --stdin cannot be used together."""
        with cli_runner.isolated_filesystem():
            with open("cred.json", "w") as f:
                f.write("{}")

            result = cli_runner.invoke(
                cli,
                [
                    "credentials",
                    "create",
                    "--type",
                    "httpBasicAuth",
                    "--name",
                    "Test",
                    "--file",
                    "cred.json",
                    "--stdin",
                ],
                input="{}",
            )

        assert result.exit_code == 1
        assert "Cannot use both --file and --stdin" in result.output

    def test_credentials_create_api_validation_error(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_credential_input: dict,
    ) -> None:
        """Test that API validation errors are handled properly."""
        from n8n_cli.exceptions import ValidationError

        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._create_credential",
                new_callable=AsyncMock,
                side_effect=ValidationError("Invalid credential type"),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "credentials",
                    "create",
                    "--type",
                    "invalidType",
                    "--name",
                    "Test",
                    "--stdin",
                ],
                input=json.dumps(sample_credential_input),
            )

        assert result.exit_code == 1
        assert "Invalid credential type" in result.output

    def test_credentials_create_requires_type_and_name(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --type and --name are required options."""
        result = cli_runner.invoke(
            credentials, ["create", "--stdin"], input="{}"
        )

        assert result.exit_code != 0
        # Click will show error about missing required options

    def test_credentials_create_json_must_be_object(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that JSON arrays or primitives are rejected."""
        with patch(
            "n8n_cli.commands.credentials.require_config", return_value=mock_config
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "credentials",
                    "create",
                    "--type",
                    "httpBasicAuth",
                    "--name",
                    "Test",
                    "--stdin",
                ],
                input="[1, 2, 3]",
            )

        assert result.exit_code == 1
        assert "must be an object" in result.output


class TestCredentialsDelete:
    """Tests for credentials delete command."""

    def test_credentials_delete_with_confirm(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test deleting credential with --confirm flag."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._delete_credential",
                new_callable=AsyncMock,
            ),
        ):
            result = cli_runner.invoke(
                credentials, ["delete", "abc123", "--confirm"]
            )

        assert result.exit_code == 0
        assert "deleted successfully" in result.output

    def test_credentials_delete_with_force(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test deleting credential with --force flag."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._delete_credential",
                new_callable=AsyncMock,
            ),
        ):
            result = cli_runner.invoke(
                credentials, ["delete", "abc123", "--force"]
            )

        assert result.exit_code == 0
        assert "deleted successfully" in result.output

    def test_credentials_delete_requires_confirmation(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that delete requires --confirm or --force."""
        result = cli_runner.invoke(cli, ["credentials", "delete", "abc123"])

        assert result.exit_code == 1
        assert "Deletion requires confirmation" in result.output

    def test_credentials_delete_not_found(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test deleting non-existent credential."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._delete_credential",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Credential not found: xyz"),
            ),
        ):
            result = cli_runner.invoke(
                cli, ["credentials", "delete", "xyz", "--confirm"]
            )

        assert result.exit_code == 1
        assert "Credential not found" in result.output

    def test_credentials_delete_requires_configuration(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that delete fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.credentials.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(
                cli, ["credentials", "delete", "abc123", "--confirm"]
            )

        assert result.exit_code == 2
        assert "Not configured" in result.output


class TestCredentialsSchema:
    """Tests for credentials schema command."""

    def test_credentials_schema_success(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_schema_response: dict,
    ) -> None:
        """Test getting credential schema."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credential_schema",
                new_callable=AsyncMock,
                return_value=sample_schema_response,
            ),
        ):
            result = cli_runner.invoke(credentials, ["schema", "httpBasicAuth"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "properties" in output
        assert "user" in output["properties"]
        assert "password" in output["properties"]

    def test_credentials_schema_not_found(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test schema for unknown credential type."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credential_schema",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Credential type not found: unknownType"),
            ),
        ):
            result = cli_runner.invoke(
                cli, ["credentials", "schema", "unknownType"]
            )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_credentials_schema_requires_configuration(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that schema fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.credentials.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(cli, ["credentials", "schema", "httpBasicAuth"])

        assert result.exit_code == 2
        assert "Not configured" in result.output


class TestCredentialsRegistration:
    """Tests for credentials command registration."""

    def test_credentials_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test credentials command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "credentials" in result.output

    def test_credentials_create_in_subcommands(self, cli_runner: CliRunner) -> None:
        """Test create subcommand is available."""
        result = cli_runner.invoke(credentials, ["--help"])
        assert "create" in result.output

    def test_credentials_delete_in_subcommands(self, cli_runner: CliRunner) -> None:
        """Test delete subcommand is available."""
        result = cli_runner.invoke(credentials, ["--help"])
        assert "delete" in result.output

    def test_credentials_schema_in_subcommands(self, cli_runner: CliRunner) -> None:
        """Test schema subcommand is available."""
        result = cli_runner.invoke(credentials, ["--help"])
        assert "schema" in result.output


class TestCredentialsClient:
    """Tests for N8nClient credential methods."""

    @pytest.mark.asyncio
    async def test_create_credential_success(
        self, sample_credential_response: dict
    ) -> None:
        """Test create_credential creates and returns credential."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = sample_credential_response
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_post = AsyncMock(return_value=mock_response)
            client._client.post = mock_post
            result = await client.create_credential(
                name="New Credential",
                credential_type="httpBasicAuth",
                data={"user": "admin", "password": "secret"},
            )

            assert result["id"] == "123"
            assert result["name"] == "New Credential"
            # Verify the payload was correct
            call_args = mock_post.call_args
            assert call_args[1]["json"]["name"] == "New Credential"
            assert call_args[1]["json"]["type"] == "httpBasicAuth"
            assert call_args[1]["json"]["data"]["user"] == "admin"

    @pytest.mark.asyncio
    async def test_delete_credential_success(self) -> None:
        """Test delete_credential deletes credential."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_delete = AsyncMock(return_value=mock_response)
            client._client.delete = mock_delete
            await client.delete_credential("abc123")

            # Verify the correct endpoint was called
            mock_delete.assert_called_once_with("/api/v1/credentials/abc123")

    @pytest.mark.asyncio
    async def test_delete_credential_not_found(self) -> None:
        """Test delete_credential raises NotFoundError on 404."""
        import httpx

        from n8n_cli.client import N8nClient
        from n8n_cli.exceptions import NotFoundError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=httpx.Request("DELETE", "http://test"),
            response=httpx.Response(404),
        )

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.delete = AsyncMock(return_value=mock_response)
            with pytest.raises(NotFoundError, match="Credential not found"):
                await client.delete_credential("xyz")

    @pytest.mark.asyncio
    async def test_get_credential_schema_success(
        self, sample_schema_response: dict
    ) -> None:
        """Test get_credential_schema returns schema."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = sample_schema_response
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_get = AsyncMock(return_value=mock_response)
            client._client.get = mock_get
            result = await client.get_credential_schema("httpBasicAuth")

            assert "properties" in result
            mock_get.assert_called_once_with("/api/v1/credentials/schema/httpBasicAuth")

    @pytest.mark.asyncio
    async def test_get_credential_schema_not_found(self) -> None:
        """Test get_credential_schema raises NotFoundError on 404."""
        import httpx

        from n8n_cli.client import N8nClient
        from n8n_cli.exceptions import NotFoundError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404),
        )

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            with pytest.raises(NotFoundError, match="Credential type not found"):
                await client.get_credential_schema("unknownType")
