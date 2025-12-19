"""Workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
from typing import Any

import click

from n8n_cli.client import N8nClient
from n8n_cli.config import require_config
from n8n_cli.output import format_datetime, get_formatter_from_context


@click.command()
@click.argument("workflow_id")
@click.pass_context
def workflow(ctx: click.Context, workflow_id: str) -> None:
    """Get detailed information about a specific workflow.

    Returns the full workflow definition including nodes and connections as JSON.
    """
    formatter = get_formatter_from_context(ctx)

    # Load config (raises ConfigError if not configured)
    config = require_config()

    # Fetch workflow (require_config guarantees these are not None)
    assert config.api_url is not None
    assert config.api_key is not None

    result = asyncio.run(
        _fetch_workflow(
            config.api_url,
            config.api_key,
            workflow_id,
        )
    )

    # Output workflow details
    formatter.output_dict(
        result,
        fields=["id", "name", "active", "createdAt", "updatedAt", "nodes", "connections"],
        labels={
            "id": "ID",
            "name": "Name",
            "active": "Active",
            "createdAt": "Created",
            "updatedAt": "Updated",
            "nodes": "Nodes",
            "connections": "Connections",
        },
        formatters={
            "createdAt": format_datetime,
            "updatedAt": format_datetime,
        },
    )


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
