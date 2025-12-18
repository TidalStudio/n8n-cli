"""Workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click
import httpx
from rich.console import Console

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config

console = Console()


@click.command()
@click.argument("workflow_id")
def workflow(workflow_id: str) -> None:
    """Get detailed information about a specific workflow.

    Returns the full workflow definition including nodes and connections as JSON.
    """
    # Load config
    try:
        config = require_config()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None

    # Fetch workflow (require_config guarantees these are not None)
    assert config.api_url is not None
    assert config.api_key is not None

    try:
        result = asyncio.run(
            _fetch_workflow(
                config.api_url,
                config.api_key,
                workflow_id,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] Workflow not found: {workflow_id}")
        else:
            console.print(f"[red]Error:[/red] API error: {e.response.status_code}")
        raise SystemExit(1) from None

    # Output as pretty-printed JSON
    click.echo(json.dumps(result, indent=2))


async def _fetch_workflow(
    api_url: str,
    api_key: str,
    workflow_id: str,
) -> dict[str, Any]:
    """Fetch a single workflow from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID to fetch.

    Returns:
        Full workflow definition.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_workflow(workflow_id)
