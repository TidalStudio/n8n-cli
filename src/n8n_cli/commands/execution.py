"""Execution command for n8n-cli."""

from __future__ import annotations

import asyncio
from typing import Any

import click
import httpx

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config
from n8n_cli.output import STATUS_COLORS, format_datetime, get_formatter_from_context


@click.command()
@click.argument("execution_id")
@click.pass_context
def execution(ctx: click.Context, execution_id: str) -> None:
    """Get detailed information about a specific execution.

    Returns the full execution data including node outputs as JSON.
    """
    formatter = get_formatter_from_context(ctx)

    # Load config
    try:
        config = require_config()
    except ConfigurationError as e:
        formatter.output_error(str(e))
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
            formatter.output_error(f"Execution not found: {execution_id}")
        else:
            formatter.output_error(f"API error: {e.response.status_code}")
        raise SystemExit(1) from None

    def format_status(s: str) -> str:
        """Format status with color."""
        color = STATUS_COLORS.get(s, "white")
        return f"[{color}]{s}[/{color}]"

    # Output execution details
    formatter.output_dict(
        result,
        fields=["id", "workflowId", "status", "startedAt", "stoppedAt", "data"],
        labels={
            "id": "ID",
            "workflowId": "Workflow ID",
            "status": "Status",
            "startedAt": "Started",
            "stoppedAt": "Stopped",
            "data": "Data",
        },
        formatters={
            "status": format_status,
            "startedAt": format_datetime,
            "stoppedAt": format_datetime,
        },
    )


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
