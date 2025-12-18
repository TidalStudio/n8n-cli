"""Workflows command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click
from rich.console import Console

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config

console = Console()


@click.command()
@click.option("--active", is_flag=True, help="Filter to only active workflows")
@click.option("--inactive", is_flag=True, help="Filter to only inactive workflows")
@click.option("--tag", "tags", multiple=True, help="Filter by tag name (can be repeated)")
def workflows(active: bool, inactive: bool, tags: tuple[str, ...]) -> None:
    """List all workflows in the n8n instance.

    Returns workflows as JSON with: id, name, active, tags, createdAt, updatedAt.
    """
    # Validate mutually exclusive flags
    if active and inactive:
        console.print("[red]Error:[/red] Cannot use both --active and --inactive")
        raise SystemExit(1)

    # Load config
    try:
        config = require_config()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None

    # Determine active filter
    active_filter: bool | None = None
    if active:
        active_filter = True
    elif inactive:
        active_filter = False

    # Fetch workflows (require_config guarantees these are not None)
    assert config.api_url is not None
    assert config.api_key is not None
    result = asyncio.run(
        _fetch_workflows(
            config.api_url,
            config.api_key,
            active_filter,
            list(tags) if tags else None,
        )
    )

    # Output as pretty-printed JSON
    click.echo(json.dumps(result, indent=2))


async def _fetch_workflows(
    api_url: str,
    api_key: str,
    active: bool | None,
    tags: list[str] | None,
) -> list[dict[str, Any]]:
    """Fetch workflows from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        active: Filter by active status (None = all).
        tags: Filter by tag names.

    Returns:
        List of workflow dictionaries.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_workflows(active=active, tags=tags)
