"""Create workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click

from n8n_cli.client import N8nClient
from n8n_cli.config import require_config
from n8n_cli.exceptions import ValidationError
from n8n_cli.output import format_datetime, get_formatter_from_context


@click.command()
@click.option(
    "--file",
    "-f",
    "file_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to workflow JSON file.",
)
@click.option(
    "--stdin",
    "use_stdin",
    is_flag=True,
    help="Read workflow JSON from stdin.",
)
@click.option(
    "--name",
    "-n",
    "name_override",
    help="Override the workflow name in the definition.",
)
@click.option(
    "--activate",
    "-a",
    is_flag=True,
    help="Activate the workflow immediately after creation.",
)
@click.pass_context
def create(
    ctx: click.Context,
    file_path: Path | None,
    use_stdin: bool,
    name_override: str | None,
    activate: bool,
) -> None:
    """Create a new workflow from a JSON definition.

    Reads workflow JSON from a file or stdin and creates it in the n8n instance.
    Returns the created workflow JSON with the new ID.

    Examples:

        n8n-cli create --file workflow.json

        cat workflow.json | n8n-cli create --stdin

        n8n-cli create --file workflow.json --name "My Workflow" --activate
    """
    formatter = get_formatter_from_context(ctx)

    # Validate input source
    if not file_path and not use_stdin:
        raise ValidationError("Must specify either --file or --stdin")

    if file_path and use_stdin:
        raise ValidationError("Cannot use both --file and --stdin")

    # Read JSON content
    try:
        json_content = (
            file_path.read_text(encoding="utf-8") if file_path else sys.stdin.read()
        )
    except OSError as e:
        raise ValidationError(f"Failed to read input: {e}") from e

    # Parse JSON
    try:
        workflow_data = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise ValidationError(
            f"Invalid JSON - {e.msg} at line {e.lineno}, column {e.colno}"
        ) from e

    if not isinstance(workflow_data, dict):
        raise ValidationError(
            "Invalid JSON - workflow must be an object, not a list or primitive"
        )

    # Validate required fields
    if "nodes" not in workflow_data:
        raise ValidationError("Workflow definition missing required field 'nodes'")

    # Apply name override or validate name exists
    if name_override:
        workflow_data["name"] = name_override
    elif "name" not in workflow_data:
        raise ValidationError("Workflow definition missing 'name'. Use --name to specify.")

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    # Create workflow
    result = asyncio.run(
        _create_workflow(
            config.api_url,
            config.api_key,
            workflow_data,
            activate,
        )
    )

    # Output created workflow
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


async def _create_workflow(
    api_url: str,
    api_key: str,
    workflow_data: dict[str, Any],
    activate: bool,
) -> dict[str, Any]:
    """Create a workflow and optionally activate it.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_data: The workflow definition.
        activate: Whether to activate the workflow after creation.

    Returns:
        Created (and possibly activated) workflow.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        result = await client.create_workflow(workflow_data)

        if activate:
            workflow_id = result.get("id")
            if workflow_id:
                result = await client.activate_workflow(str(workflow_id))

        return result
