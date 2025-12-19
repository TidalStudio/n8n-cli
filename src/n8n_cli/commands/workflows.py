"""Workflows command for n8n-cli."""

from __future__ import annotations

import asyncio
from typing import Any

import click

from n8n_cli.client import N8nClient
from n8n_cli.config import require_config
from n8n_cli.exceptions import ValidationError
from n8n_cli.output import format_datetime, get_formatter_from_context, truncate


@click.command()
@click.option("--active", is_flag=True, help="Filter to only active workflows")
@click.option("--inactive", is_flag=True, help="Filter to only inactive workflows")
@click.option("--tag", "tags", multiple=True, help="Filter by tag name (can be repeated)")
@click.option(
    "--summary",
    is_flag=True,
    help="Return only essential fields (id, name, active, createdAt, updatedAt, tags)",
)
@click.pass_context
def workflows(
    ctx: click.Context, active: bool, inactive: bool, tags: tuple[str, ...], summary: bool
) -> None:
    """List all workflows in the n8n instance.

    Returns workflows as JSON with: id, name, active, tags, createdAt, updatedAt.
    """
    formatter = get_formatter_from_context(ctx)

    # Validate mutually exclusive flags
    if active and inactive:
        raise ValidationError("Cannot use both --active and --inactive")

    # Load config (raises ConfigError if not configured)
    config = require_config()

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

    # If summary mode, strip down to essential fields only
    if summary:
        result = _summarize_workflows(result)

    # Output with formatter
    formatter.output_list(
        result,
        columns=["id", "name", "active", "updatedAt"],
        headers=["ID", "Name", "Active", "Updated"],
        formatters={
            "name": lambda x: truncate(str(x), 40),
            "updatedAt": format_datetime,
        },
    )


def _summarize_workflows(workflows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip workflows down to essential fields only.

    Args:
        workflows: Full workflow data from API.

    Returns:
        List of workflows with only id, name, active, createdAt, updatedAt, tags.
    """
    summary_fields = {"id", "name", "active", "createdAt", "updatedAt", "tags"}
    return [{k: v for k, v in wf.items() if k in summary_fields} for wf in workflows]


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
