"""Create workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
import httpx
from rich.console import Console

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config

console = Console()


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
def create(
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
    # Validate input source
    if not file_path and not use_stdin:
        console.print("[red]Error:[/red] Must specify either --file or --stdin")
        raise SystemExit(1)

    if file_path and use_stdin:
        console.print("[red]Error:[/red] Cannot use both --file and --stdin")
        raise SystemExit(1)

    # Read JSON content
    try:
        json_content = (
            file_path.read_text(encoding="utf-8") if file_path else sys.stdin.read()
        )
    except OSError as e:
        console.print(f"[red]Error:[/red] Failed to read input: {e}")
        raise SystemExit(1) from None

    # Parse JSON
    try:
        workflow_data = json.loads(json_content)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON - {e.msg} at line {e.lineno}, column {e.colno}")
        raise SystemExit(1) from None

    if not isinstance(workflow_data, dict):
        console.print("[red]Error:[/red] Invalid JSON - workflow must be an object, not a list or primitive")
        raise SystemExit(1)

    # Validate required fields
    if "nodes" not in workflow_data:
        console.print("[red]Error:[/red] Workflow definition missing required field 'nodes'")
        raise SystemExit(1)

    # Apply name override or validate name exists
    if name_override:
        workflow_data["name"] = name_override
    elif "name" not in workflow_data:
        console.print("[red]Error:[/red] Workflow definition missing 'name'. Use --name to specify.")
        raise SystemExit(1)

    # Load config
    try:
        config = require_config()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None

    assert config.api_url is not None
    assert config.api_key is not None

    # Create workflow
    try:
        result = asyncio.run(
            _create_workflow(
                config.api_url,
                config.api_key,
                workflow_data,
                activate,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            # Try to extract error message from response
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except (json.JSONDecodeError, KeyError):
                error_msg = str(e)
            console.print(f"[red]Error:[/red] Validation failed - {error_msg}")
        elif e.response.status_code == 409:
            console.print("[red]Error:[/red] Workflow with this name already exists")
        else:
            console.print(f"[red]Error:[/red] API error: {e.response.status_code}")
        raise SystemExit(1) from None

    # Output created workflow
    click.echo(json.dumps(result, indent=2))


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
