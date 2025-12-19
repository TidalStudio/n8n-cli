"""Enable workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click
import httpx

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config
from n8n_cli.output import format_datetime, get_formatter_from_context


@click.command()
@click.argument("workflow_id")
@click.pass_context
def enable(ctx: click.Context, workflow_id: str) -> None:
    """Enable (activate) a workflow by ID.

    Activates a workflow so it can be triggered via webhooks or schedules.
    This operation is idempotent - enabling an already-active workflow succeeds.

    Examples:

        n8n-cli enable 123

        n8n-cli enable abc-def-123
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
            _enable_workflow(
                api_url=config.api_url,
                api_key=config.api_key,
                workflow_id=workflow_id,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            formatter.output_error(f"Workflow '{workflow_id}' not found")
        elif e.response.status_code == 400:
            try:
                error_data = e.response.json()
                msg = error_data.get("message", str(e))
            except (json.JSONDecodeError, KeyError):
                msg = str(e)
            formatter.output_error(msg)
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
