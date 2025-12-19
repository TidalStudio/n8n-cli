"""Disable workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
from typing import Any

import click
import httpx

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config
from n8n_cli.output import format_datetime, get_formatter_from_context


@click.command()
@click.argument("workflow_id")
@click.pass_context
def disable(ctx: click.Context, workflow_id: str) -> None:
    """Disable (deactivate) a workflow by ID.

    Deactivates a workflow so it will no longer be triggered via webhooks or schedules.
    This operation is idempotent - disabling an already-inactive workflow succeeds.

    Examples:

        n8n-cli disable 123

        n8n-cli disable abc-def-123
    """
    formatter = get_formatter_from_context(ctx)

    try:
        config = require_config()
    except ConfigurationError as e:
        formatter.output_error(str(e))
        raise SystemExit(1) from None

    assert config.api_url is not None
    assert config.api_key is not None

    try:
        result = asyncio.run(
            _disable_workflow(
                api_url=config.api_url,
                api_key=config.api_key,
                workflow_id=workflow_id,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            formatter.output_error(f"Workflow '{workflow_id}' not found")
        else:
            formatter.output_error(f"API error: {e.response.status_code}")
        raise SystemExit(1) from None

    formatter.output_dict(
        result,
        fields=["id", "name", "active", "createdAt", "updatedAt"],
        labels={
            "id": "ID",
            "name": "Name",
            "active": "Active",
            "createdAt": "Created",
            "updatedAt": "Updated",
        },
        formatters={
            "createdAt": format_datetime,
            "updatedAt": format_datetime,
        },
    )


async def _disable_workflow(
    api_url: str,
    api_key: str,
    workflow_id: str,
) -> dict[str, Any]:
    """Disable a workflow by ID.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID to disable.

    Returns:
        Updated workflow data.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        return await client.deactivate_workflow(workflow_id)
