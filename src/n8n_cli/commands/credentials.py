"""Credentials commands for n8n-cli."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click

from n8n_cli.client import N8nClient
from n8n_cli.config import require_config
from n8n_cli.exceptions import ValidationError
from n8n_cli.output import format_datetime, get_formatter_from_context, truncate

# Sensitive field patterns to mask (lowercase for case-insensitive matching)
SENSITIVE_PATTERNS = {
    "password",
    "secret",
    "token",
    "key",
    "apikey",
    "apisecret",
    "accesstoken",
    "refreshtoken",
    "privatekey",
    "clientsecret",
}


def mask_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask sensitive fields in credential data.

    Args:
        data: The credential data dictionary.

    Returns:
        Dictionary with sensitive values replaced by "***".
    """
    if not isinstance(data, dict):
        return data

    masked: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        # Check if key contains any sensitive pattern
        is_sensitive = any(pattern in key_lower for pattern in SENSITIVE_PATTERNS)

        if is_sensitive and isinstance(value, str) and value:
            masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value)
        else:
            masked[key] = value
    return masked


@click.group()
def credentials() -> None:
    """Manage n8n credentials."""
    pass


@credentials.command("list")
@click.option("--type", "cred_type", help="Filter by credential type (e.g., httpBasicAuth)")
@click.pass_context
def credentials_list(ctx: click.Context, cred_type: str | None) -> None:
    """List all credentials in the n8n instance.

    Returns credentials as JSON with: id, name, type, createdAt, updatedAt.
    Sensitive credential data is not included in list output.

    Examples:

        n8n-cli credentials list

        n8n-cli credentials list --type httpBasicAuth

        n8n-cli credentials list --format table
    """
    formatter = get_formatter_from_context(ctx)

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    result = asyncio.run(
        _fetch_credentials(
            config.api_url,
            config.api_key,
            cred_type,
        )
    )

    # Output with formatter
    formatter.output_list(
        result,
        columns=["id", "name", "type", "updatedAt"],
        headers=["ID", "Name", "Type", "Updated"],
        formatters={
            "name": lambda x: truncate(str(x), 40),
            "updatedAt": format_datetime,
        },
    )


async def _fetch_credentials(
    api_url: str,
    api_key: str,
    cred_type: str | None,
) -> list[dict[str, Any]]:
    """Fetch credentials from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        cred_type: Filter by credential type.

    Returns:
        List of credential dictionaries.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_credentials(credential_type=cred_type)


@credentials.command("show")
@click.argument("credential_id")
@click.pass_context
def credentials_show(ctx: click.Context, credential_id: str) -> None:
    """Get detailed information about a specific credential.

    Returns credential details with sensitive data masked (shown as ***).

    Examples:

        n8n-cli credentials show 123

        n8n-cli credentials show 123 --format table
    """
    formatter = get_formatter_from_context(ctx)

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    result = asyncio.run(
        _fetch_credential(
            config.api_url,
            config.api_key,
            credential_id,
        )
    )

    # Mask sensitive fields in the data
    if "data" in result:
        result["data"] = mask_sensitive_data(result["data"])

    # Output credential details
    formatter.output_dict(
        result,
        fields=["id", "name", "type", "createdAt", "updatedAt", "data"],
        labels={
            "id": "ID",
            "name": "Name",
            "type": "Type",
            "createdAt": "Created",
            "updatedAt": "Updated",
            "data": "Data (masked)",
        },
        formatters={
            "createdAt": format_datetime,
            "updatedAt": format_datetime,
        },
    )


async def _fetch_credential(
    api_url: str,
    api_key: str,
    credential_id: str,
) -> dict[str, Any]:
    """Fetch a single credential from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        credential_id: The credential ID to fetch.

    Returns:
        Credential dictionary.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_credential(credential_id)


@credentials.command("create")
@click.option(
    "--type",
    "cred_type",
    required=True,
    help="Credential type (e.g., httpBasicAuth, oAuth2Api).",
)
@click.option(
    "--name",
    "-n",
    required=True,
    help="Display name for the credential.",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to credential data JSON file.",
)
@click.option(
    "--stdin",
    "use_stdin",
    is_flag=True,
    help="Read credential data JSON from stdin.",
)
@click.pass_context
def credentials_create(
    ctx: click.Context,
    cred_type: str,
    name: str,
    file_path: Path | None,
    use_stdin: bool,
) -> None:
    """Create a new credential from JSON data.

    Reads credential data JSON from a file or stdin and creates the credential
    in the n8n instance.

    Examples:

        echo '{"user": "admin", "password": "secret"}' | n8n-cli credentials create --type httpBasicAuth --name "My Auth" --stdin

        n8n-cli credentials create --type httpBasicAuth --name "My Auth" --file cred-data.json
    """
    formatter = get_formatter_from_context(ctx)

    # Validate input source
    if not file_path and not use_stdin:
        raise ValidationError("Must specify either --file or --stdin")

    if file_path and use_stdin:
        raise ValidationError("Cannot use both --file and --stdin")

    # Read JSON content
    try:
        json_content = (
            file_path.read_text(encoding="utf-8") if file_path else sys.stdin.read()
        )
    except OSError as e:
        raise ValidationError(f"Failed to read input: {e}") from e

    if not json_content.strip():
        raise ValidationError("No input provided. Provide credential data via --file or --stdin.")

    # Parse JSON
    try:
        cred_data = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise ValidationError(
            f"Invalid JSON - {e.msg} at line {e.lineno}, column {e.colno}"
        ) from e

    if not isinstance(cred_data, dict):
        raise ValidationError(
            "Invalid JSON - credential data must be an object, not a list or primitive"
        )

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    result = asyncio.run(
        _create_credential(
            config.api_url,
            config.api_key,
            name,
            cred_type,
            cred_data,
        )
    )

    # Mask sensitive data before output
    if "data" in result:
        result["data"] = mask_sensitive_data(result["data"])

    # Output created credential
    formatter.output_dict(
        result,
        fields=["id", "name", "type", "createdAt"],
        labels={
            "id": "ID",
            "name": "Name",
            "type": "Type",
            "createdAt": "Created",
        },
        formatters={
            "createdAt": format_datetime,
        },
    )


async def _create_credential(
    api_url: str,
    api_key: str,
    name: str,
    cred_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Create a credential in n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        name: Display name for the credential.
        cred_type: The credential type.
        data: The credential data.

    Returns:
        Created credential dictionary.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.create_credential(name, cred_type, data)
