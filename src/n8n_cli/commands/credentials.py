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
from n8n_cli.output import format_datetime, get_formatter_from_context


@click.group()
def credentials() -> None:
    """Manage n8n credentials."""
    pass


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
    in the n8n instance. Use 'credentials schema' to see required fields for
    a credential type.

    Examples:

        n8n-cli credentials schema httpBasicAuth

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


@credentials.command("delete")
@click.argument("credential_id")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm deletion without prompting.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force deletion (same as --confirm, for scripting).",
)
@click.pass_context
def credentials_delete(
    ctx: click.Context,
    credential_id: str,
    confirm: bool,
    force: bool,
) -> None:
    """Delete a credential by ID.

    Requires confirmation via --confirm or --force flag.

    Examples:

        n8n-cli credentials delete abc123 --confirm

        n8n-cli credentials delete abc123 --force
    """
    formatter = get_formatter_from_context(ctx)

    # Require confirmation
    if not confirm and not force:
        raise ValidationError(
            "Deletion requires confirmation. Use --confirm flag or --force for scripting."
        )

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    asyncio.run(
        _delete_credential(
            config.api_url,
            config.api_key,
            credential_id,
        )
    )

    formatter.output_success(f"Credential {credential_id} deleted successfully.")


async def _delete_credential(
    api_url: str,
    api_key: str,
    credential_id: str,
) -> None:
    """Delete a credential from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        credential_id: The credential ID to delete.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        await client.delete_credential(credential_id)


@credentials.command("schema")
@click.argument("credential_type")
@click.pass_context
def credentials_schema(ctx: click.Context, credential_type: str) -> None:
    """Show the required fields for a credential type.

    Use this to discover what data fields are needed when creating
    a credential of a specific type.

    Examples:

        n8n-cli credentials schema httpBasicAuth

        n8n-cli credentials schema oAuth2Api

        n8n-cli credentials schema githubApi
    """
    formatter = get_formatter_from_context(ctx)

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    result = asyncio.run(
        _fetch_credential_schema(
            config.api_url,
            config.api_key,
            credential_type,
        )
    )

    # Output the schema
    formatter.output_dict(result)


async def _fetch_credential_schema(
    api_url: str,
    api_key: str,
    credential_type: str,
) -> dict[str, Any]:
    """Fetch credential schema from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        credential_type: The credential type to get schema for.

    Returns:
        Schema dictionary with required fields.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_credential_schema(credential_type)
