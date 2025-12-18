"""Delete workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
from typing import Any

import click
import httpx
from rich.console import Console

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config

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
    # Load config early
    try:
        config = require_config()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None

    assert config.api_url is not None
    assert config.api_key is not None

    # Check confirmation flags
    if not confirm and not force:
        console.print(
            "[red]Error:[/red] Deletion requires confirmation. "
            "Use --confirm flag or --force for scripting."
        )
        raise SystemExit(1)

    # Fetch workflow first to get name and check status
    try:
        workflow = asyncio.run(
            _get_workflow(
                api_url=config.api_url,
                api_key=config.api_key,
                workflow_id=workflow_id,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] Workflow '{workflow_id}' not found")
        else:
            console.print(f"[red]Error:[/red] API error: {e.response.status_code}")
        raise SystemExit(1) from None

    workflow_name = workflow.get("name", "Unknown")
    is_active = workflow.get("active", False)

    # Warn about active workflows
    if is_active and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Workflow '{workflow_name}' is currently active."
        )
        console.print("Use --force to delete active workflows.")
        raise SystemExit(1)

    # Execute deletion
    try:
        asyncio.run(
            _delete_workflow(
                api_url=config.api_url,
                api_key=config.api_key,
                workflow_id=workflow_id,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] Workflow '{workflow_id}' not found")
        else:
            console.print(f"[red]Error:[/red] API error: {e.response.status_code}")
        raise SystemExit(1) from None

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
