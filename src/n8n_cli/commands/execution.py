"""Execution command for n8n-cli."""

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
@click.argument("execution_id")
def execution(execution_id: str) -> None:
    """Get detailed information about a specific execution.

    Returns the full execution data including node outputs as JSON.
    """
    # Load config
    try:
        config = require_config()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None

    # Fetch execution (require_config guarantees these are not None)
    assert config.api_url is not None
    assert config.api_key is not None

    try:
        result = asyncio.run(
            _fetch_execution(
                config.api_url,
                config.api_key,
                execution_id,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] Execution not found: {execution_id}")
        else:
            console.print(f"[red]Error:[/red] API error: {e.response.status_code}")
        raise SystemExit(1) from None

    # Output as pretty-printed JSON
    click.echo(json.dumps(result, indent=2))


async def _fetch_execution(
    api_url: str,
    api_key: str,
    execution_id: str,
) -> dict[str, Any]:
    """Fetch a single execution from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        execution_id: The execution ID to fetch.

    Returns:
        Full execution data including node outputs.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_execution(execution_id)
