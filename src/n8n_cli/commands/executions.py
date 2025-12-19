"""Executions command for n8n-cli."""

from __future__ import annotations

import asyncio
from typing import Any

import click

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config
from n8n_cli.output import STATUS_COLORS, format_datetime, get_formatter_from_context

VALID_STATUSES = ["success", "error", "running", "waiting", "canceled"]


@click.command()
@click.option("--workflow", help="Filter by workflow ID")
@click.option(
    "--status",
    type=click.Choice(VALID_STATUSES, case_sensitive=False),
    help="Filter by execution status",
)
@click.option("--limit", default=20, help="Number of results (default: 20, max: 250)")
@click.pass_context
def executions(
    ctx: click.Context,
    workflow: str | None,
    status: str | None,
    limit: int,
) -> None:
    """List workflow executions.

    Returns executions as JSON with: id, workflowId, status, startedAt, stoppedAt.
    """
    formatter = get_formatter_from_context(ctx)

    # Load config
    try:
        config = require_config()
    except ConfigurationError as e:
        formatter.output_error(str(e))
        raise SystemExit(1) from None

    assert config.api_url is not None
    assert config.api_key is not None

    # Fetch executions
    result = asyncio.run(
        _fetch_executions(config.api_url, config.api_key, workflow, status, limit)
    )

    def format_status(s: str) -> str:
        """Format status with color."""
        color = STATUS_COLORS.get(s, "white")
        return f"[{color}]{s}[/{color}]"

    formatter.output_list(
        result,
        columns=["id", "workflowId", "status", "startedAt", "stoppedAt"],
        headers=["ID", "Workflow", "Status", "Started", "Stopped"],
        formatters={
            "status": format_status,
            "startedAt": format_datetime,
            "stoppedAt": format_datetime,
        },
    )


async def _fetch_executions(
    api_url: str,
    api_key: str,
    workflow_id: str | None,
    status: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch executions from n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: Filter by workflow ID.
        status: Filter by execution status.
        limit: Max number of results.

    Returns:
        List of execution dictionaries.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.get_executions(
            workflow_id=workflow_id, status=status, limit=limit
        )
