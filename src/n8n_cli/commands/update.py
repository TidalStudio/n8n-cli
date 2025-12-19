"""Update workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
import httpx

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config
from n8n_cli.output import format_datetime, get_formatter_from_context


@click.command()
@click.argument("workflow_id")
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
    help="Update the workflow name.",
)
@click.option(
    "--activate",
    is_flag=True,
    help="Activate the workflow.",
)
@click.option(
    "--deactivate",
    is_flag=True,
    help="Deactivate the workflow.",
)
@click.pass_context
def update(
    ctx: click.Context,
    workflow_id: str,
    file_path: Path | None,
    use_stdin: bool,
    name_override: str | None,
    activate: bool,
    deactivate: bool,
) -> None:
    """Update an existing workflow.

    Updates a workflow by ID. You can replace the entire definition using
    --file or --stdin, or make quick updates using --name, --activate,
    or --deactivate flags.

    Examples:

        n8n-cli update 123 --file workflow.json

        cat workflow.json | n8n-cli update 123 --stdin

        n8n-cli update 123 --name "New Workflow Name"

        n8n-cli update 123 --activate

        n8n-cli update 123 --file workflow.json --name "Override Name" --activate
    """
    formatter = get_formatter_from_context(ctx)

    # Validate mutual exclusivity
    if file_path and use_stdin:
        formatter.output_error("Cannot use both --file and --stdin")
        raise SystemExit(1)

    if activate and deactivate:
        formatter.output_error("Cannot use both --activate and --deactivate")
        raise SystemExit(1)

    # Check that at least one modification is specified
    has_file_input = file_path or use_stdin
    has_quick_update = name_override or activate or deactivate

    if not has_file_input and not has_quick_update:
        formatter.output_error(
            "Must specify --file, --stdin, or a modification flag "
            "(--name, --activate, --deactivate)"
        )
        raise SystemExit(1)

    # Load config early
    try:
        config = require_config()
    except ConfigurationError as e:
        formatter.output_error(str(e))
        raise SystemExit(1) from None

    assert config.api_url is not None
    assert config.api_key is not None

    # Determine workflow data source
    workflow_data: dict[str, Any] | None = None

    if has_file_input:
        # Read JSON from file or stdin
        try:
            json_content = (
                file_path.read_text(encoding="utf-8") if file_path else sys.stdin.read()
            )
        except OSError as e:
            formatter.output_error(f"Failed to read input: {e}")
            raise SystemExit(1) from None

        # Parse JSON
        try:
            workflow_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            formatter.output_error(
                f"Invalid JSON - {e.msg} at line {e.lineno}, column {e.colno}"
            )
            raise SystemExit(1) from None

        if not isinstance(workflow_data, dict):
            formatter.output_error(
                "Invalid JSON - workflow must be an object, not a list or primitive"
            )
            raise SystemExit(1)

        # Validate required fields for full update
        if "nodes" not in workflow_data:
            formatter.output_error("Workflow definition missing required field 'nodes'")
            raise SystemExit(1)

        # Strip ID from input - we use the CLI argument
        workflow_data.pop("id", None)

    # Execute update
    try:
        result = asyncio.run(
            _update_workflow(
                api_url=config.api_url,
                api_key=config.api_key,
                workflow_id=workflow_id,
                workflow_data=workflow_data,
                name_override=name_override,
                activate=activate,
                deactivate=deactivate,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except (json.JSONDecodeError, KeyError):
                error_msg = str(e)
            formatter.output_error(f"Validation failed - {error_msg}")
        elif e.response.status_code == 404:
            formatter.output_error(f"Workflow '{workflow_id}' not found")
        else:
            formatter.output_error(f"API error: {e.response.status_code}")
        raise SystemExit(1) from None

    # Output updated workflow
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


async def _update_workflow(
    api_url: str,
    api_key: str,
    workflow_id: str,
    workflow_data: dict[str, Any] | None,
    name_override: str | None,
    activate: bool,
    deactivate: bool,
) -> dict[str, Any]:
    """Update a workflow with the specified changes.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID to update.
        workflow_data: Full workflow definition (if provided via file/stdin).
        name_override: New name for the workflow (optional).
        activate: Whether to activate the workflow.
        deactivate: Whether to deactivate the workflow.

    Returns:
        Updated workflow.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        # If no file input, fetch existing workflow
        if workflow_data is None:
            workflow_data = await client.get_workflow(workflow_id)

        # Apply modifications
        if name_override:
            workflow_data["name"] = name_override

        if activate:
            workflow_data["active"] = True
        elif deactivate:
            workflow_data["active"] = False

        # Send update
        return await client.update_workflow(workflow_id, workflow_data)
