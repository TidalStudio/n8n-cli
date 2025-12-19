"""Enable workflow command for n8n-cli."""

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
def enable(workflow_id: str) -> None:
    """Enable (activate) a workflow by ID.

    Activates a workflow so it can be triggered via webhooks or schedules.
    This operation is idempotent - enabling an already-active workflow succeeds.

    Examples:

        n8n-cli enable 123

        n8n-cli enable abc-def-123
    """
    try:
        config = require_config()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None

    assert config.api_url is not None
    assert config.api_key is not None

    try:
        result = asyncio.run(
            _enable_workflow(
                api_url=config.api_url,
                api_key=config.api_key,
                workflow_id=workflow_id,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] Workflow '{workflow_id}' not found")
        elif e.response.status_code == 400:
            try:
                error_data = e.response.json()
                msg = error_data.get("message", str(e))
            except (json.JSONDecodeError, KeyError):
                msg = str(e)
            console.print(f"[red]Error:[/red] {msg}")
        else:
            console.print(f"[red]Error:[/red] API error: {e.response.status_code}")
        raise SystemExit(1) from None

    click.echo(json.dumps(result, indent=2))


async def _enable_workflow(
    api_url: str,
    api_key: str,
    workflow_id: str,
) -> dict[str, Any]:
    """Enable a workflow by ID.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID to enable.

    Returns:
        Updated workflow data.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.activate_workflow(workflow_id)
