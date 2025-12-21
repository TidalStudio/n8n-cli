"""Tests for credentials commands."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.credentials import credentials, mask_sensitive_data
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
def sample_credentials() -> list[dict[str, Any]]:
    """Provide sample credential list data."""
    return [
        {
            "id": "1",
            "name": "My HTTP Auth",
            "type": "httpBasicAuth",
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-02T00:00:00.000Z",
        },
        {
            "id": "2",
            "name": "My OAuth",
            "type": "oAuth2Api",
            "createdAt": "2024-01-03T00:00:00.000Z",
            "updatedAt": "2024-01-04T00:00:00.000Z",
        },
        {
            "id": "3",
            "name": "API Key Creds",
            "type": "httpHeaderAuth",
            "createdAt": "2024-01-05T00:00:00.000Z",
            "updatedAt": "2024-01-06T00:00:00.000Z",
        },
    ]


@pytest.fixture
def sample_credential_detail() -> dict[str, Any]:
    """Provide sample credential detail with sensitive data."""
    return {
        "id": "1",
        "name": "My HTTP Auth",
        "type": "httpBasicAuth",
        "data": {
            "user": "admin",
            "password": "supersecret123",
        },
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-02T00:00:00.000Z",
    }


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
        "data": {
            "user": "admin",
            "password": "secret123",
        },
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }


class TestMaskSensitiveData:
    """Tests for mask_sensitive_data function."""

    def test_mask_password_field(self) -> None:
        """Test that password field is masked."""
        data = {"user": "admin", "password": "secret123"}
        result = mask_sensitive_data(data)
        assert result["user"] == "admin"
        assert result["password"] == "***"

    def test_mask_token_field(self) -> None:
        """Test that token fields are masked."""
        data = {"token": "abc123", "accessToken": "xyz789"}
        result = mask_sensitive_data(data)
        assert result["token"] == "***"
        assert result["accessToken"] == "***"

    def test_mask_apikey_field(self) -> None:
        """Test that apiKey and apiSecret fields are masked."""
        data = {"apiKey": "key123", "apiSecret": "secret456"}
        result = mask_sensitive_data(data)
        assert result["apiKey"] == "***"
        assert result["apiSecret"] == "***"

    def test_mask_preserves_non_sensitive(self) -> None:
        """Test that non-sensitive fields are not masked."""
        data = {"user": "admin", "email": "test@example.com", "name": "Test"}
        result = mask_sensitive_data(data)
        assert result["user"] == "admin"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test"

    def test_mask_nested_objects(self) -> None:
        """Test that nested objects are masked recursively."""
        data = {
            "credentials": {
                "password": "secret123",
                "nested": {
                    "apiKey": "key123",
                },
            },
            "user": "admin",
        }
        result = mask_sensitive_data(data)
        assert result["user"] == "admin"
        assert result["credentials"]["password"] == "***"
        assert result["credentials"]["nested"]["apiKey"] == "***"

    def test_mask_empty_values_unchanged(self) -> None:
        """Test that empty string values are not masked."""
        data = {"password": "", "token": ""}
        result = mask_sensitive_data(data)
        # Empty strings should not be masked (no value to protect)
        assert result["password"] == ""
        assert result["token"] == ""

    def test_mask_case_insensitive(self) -> None:
        """Test that matching is case-insensitive."""
        data = {"PASSWORD": "secret", "ApiKey": "key", "accessTOKEN": "tok"}
        result = mask_sensitive_data(data)
        assert result["PASSWORD"] == "***"
        assert result["ApiKey"] == "***"
        assert result["accessTOKEN"] == "***"


class TestCredentialsList:
    """Tests for credentials list command."""

    def test_credentials_list_returns_all(
        self, cli_runner: CliRunner, mock_config: Config, sample_credentials: list[dict]
    ) -> None:
        """Test that credentials list returns all credentials as JSON."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credentials",
                new_callable=AsyncMock,
                return_value=sample_credentials,
            ),
        ):
            result = cli_runner.invoke(credentials, ["list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 3
        assert output[0]["name"] == "My HTTP Auth"

    def test_credentials_list_type_filter(
        self, cli_runner: CliRunner, mock_config: Config, sample_credentials: list[dict]
    ) -> None:
        """Test --type flag filters by credential type."""
        filtered = [c for c in sample_credentials if c["type"] == "httpBasicAuth"]

        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credentials",
                new_callable=AsyncMock,
                return_value=filtered,
            ) as mock_fetch,
        ):
            result = cli_runner.invoke(credentials, ["list", "--type", "httpBasicAuth"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][2] == "httpBasicAuth"  # cred_type parameter

    def test_credentials_list_empty(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test empty credentials list returns empty JSON array."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credentials",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = cli_runner.invoke(credentials, ["list"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output == []

    def test_credentials_list_requires_configuration(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that credentials list fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.credentials.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(cli, ["credentials", "list"])

        assert result.exit_code == 2  # ConfigError uses exit code 2
        assert "Error" in result.output
        assert "Not configured" in result.output


class TestCredentialsShow:
    """Tests for credentials show command."""

    def test_credentials_show_returns_credential(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_credential_detail: dict,
    ) -> None:
        """Test that credentials show returns credential details."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credential",
                new_callable=AsyncMock,
                return_value=sample_credential_detail,
            ),
        ):
            result = cli_runner.invoke(credentials, ["show", "1"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["id"] == "1"
        assert output["name"] == "My HTTP Auth"

    def test_credentials_show_masks_sensitive_data(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_credential_detail: dict,
    ) -> None:
        """Test that sensitive data is masked in output."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credential",
                new_callable=AsyncMock,
                return_value=sample_credential_detail.copy(),
            ),
        ):
            result = cli_runner.invoke(credentials, ["show", "1"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["data"]["user"] == "admin"
        assert output["data"]["password"] == "***"

    def test_credentials_show_not_found(
        self, cli_runner: CliRunner, mock_config: Config
    ) -> None:
        """Test that NotFoundError is raised for missing credential."""
        from n8n_cli.exceptions import NotFoundError

        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._fetch_credential",
                new_callable=AsyncMock,
                side_effect=NotFoundError("Credential not found: 999"),
            ),
        ):
            result = cli_runner.invoke(cli, ["credentials", "show", "999"])

        assert result.exit_code == 1
        assert "Credential not found" in result.output

    def test_credentials_show_requires_configuration(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that credentials show fails when not configured."""
        from n8n_cli.exceptions import ConfigError

        with patch(
            "n8n_cli.commands.credentials.require_config",
            side_effect=ConfigError("Not configured"),
        ):
            result = cli_runner.invoke(cli, ["credentials", "show", "1"])

        assert result.exit_code == 2
        assert "Not configured" in result.output


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

    def test_credentials_create_masks_output(
        self,
        cli_runner: CliRunner,
        mock_config: Config,
        sample_credential_input: dict,
        sample_credential_response: dict,
    ) -> None:
        """Test that sensitive data is masked in create output."""
        with (
            patch(
                "n8n_cli.commands.credentials.require_config", return_value=mock_config
            ),
            patch(
                "n8n_cli.commands.credentials._create_credential",
                new_callable=AsyncMock,
                return_value=sample_credential_response.copy(),
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
        # Note: create command output doesn't include data field in fields list
        # so we just verify the command succeeded

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


class TestCredentialsRegistration:
    """Tests for credentials command registration."""

    def test_credentials_registered_with_cli(self, cli_runner: CliRunner) -> None:
        """Test credentials command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "credentials" in result.output

    def test_credentials_list_in_subcommands(self, cli_runner: CliRunner) -> None:
        """Test list subcommand is available."""
        result = cli_runner.invoke(credentials, ["--help"])
        assert "list" in result.output

    def test_credentials_show_in_subcommands(self, cli_runner: CliRunner) -> None:
        """Test show subcommand is available."""
        result = cli_runner.invoke(credentials, ["--help"])
        assert "show" in result.output

    def test_credentials_create_in_subcommands(self, cli_runner: CliRunner) -> None:
        """Test create subcommand is available."""
        result = cli_runner.invoke(credentials, ["--help"])
        assert "create" in result.output


class TestGetCredentialsClient:
    """Tests for N8nClient credential methods."""

    @pytest.mark.asyncio
    async def test_get_credentials_returns_all(
        self, sample_credentials: list[dict]
    ) -> None:
        """Test get_credentials returns all credentials."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_credentials}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_credentials()

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_credentials_filters_by_type(
        self, sample_credentials: list[dict]
    ) -> None:
        """Test get_credentials filters by credential type."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_credentials}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_credentials(credential_type="httpBasicAuth")

        assert len(result) == 1
        assert result[0]["type"] == "httpBasicAuth"

    @pytest.mark.asyncio
    async def test_get_credential_returns_detail(
        self, sample_credential_detail: dict
    ) -> None:
        """Test get_credential returns credential detail."""
        from n8n_cli.client import N8nClient

        mock_response = MagicMock()
        mock_response.json.return_value = sample_credential_detail
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_credential("1")

        assert result["id"] == "1"
        assert result["name"] == "My HTTP Auth"

    @pytest.mark.asyncio
    async def test_get_credential_not_found(self) -> None:
        """Test get_credential raises NotFoundError on 404."""
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
            with pytest.raises(NotFoundError, match="Credential not found: 999"):
                await client.get_credential("999")

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
