"""Delete workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
from typing import Any

import click
from rich.console import Console

from n8n_cli.client import N8nClient
from n8n_cli.config import require_config
from n8n_cli.exceptions import ValidationError

console = Console()


@click.command()
@click.argument("workflow_id")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm deletion of the workflow.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force deletion without confirmation (use with caution).",
)
def delete(workflow_id: str, confirm: bool, force: bool) -> None:
    """Delete a workflow by ID.

    Deletes a workflow permanently. Requires --confirm flag to prevent
    accidental deletions. Use --force to skip confirmation (for scripting).

    Examples:

        n8n-cli delete 123 --confirm

        n8n-cli delete 123 --force
    """
    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    # Check confirmation flags
    if not confirm and not force:
        raise ValidationError(
            "Deletion requires confirmation. "
            "Use --confirm flag or --force for scripting."
        )

    # Fetch workflow first to get name and check status
    workflow = asyncio.run(
        _get_workflow(
            api_url=config.api_url,
            api_key=config.api_key,
            workflow_id=workflow_id,
        )
    )

    workflow_name = workflow.get("name", "Unknown")
    is_active = workflow.get("active", False)

    # Warn about active workflows
    if is_active and not force:
        raise ValidationError(
            f"Workflow '{workflow_name}' is currently active. "
            "Use --force to delete active workflows."
        )

    # Execute deletion
    asyncio.run(
        _delete_workflow(
            api_url=config.api_url,
            api_key=config.api_key,
            workflow_id=workflow_id,
        )
    )

    console.print(f"Deleted workflow '{workflow_name}' (ID: {workflow_id})")


async def _get_workflow(
    api_url: str,
    api_key: str,
    workflow_id: str,
) -> dict[str, Any]:
    """Fetch a workflow by ID.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID to fetch.

    Returns:
        Workflow data.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_workflow(workflow_id)


async def _delete_workflow(
    api_url: str,
    api_key: str,
    workflow_id: str,
) -> None:
    """Delete a workflow by ID.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID to delete.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        await client.delete_workflow(workflow_id)
