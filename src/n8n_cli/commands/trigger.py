"""Trigger workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import click
import httpx
from rich.console import Console

from n8n_cli.client import N8nClient
from n8n_cli.config import ConfigurationError, require_config

console = Console()

# Terminal execution statuses
TERMINAL_STATUSES = {"success", "error", "crashed", "canceled"}
POLL_INTERVAL = 1.0  # seconds


@click.command()
@click.argument("workflow_id")
@click.option(
    "--data",
    "-d",
    "data_json",
    help="JSON input data to pass to the workflow.",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to JSON file containing input data.",
)
@click.option(
    "--wait",
    "-w",
    "wait_for_completion",
    is_flag=True,
    help="Wait for execution to complete and return output.",
)
@click.option(
    "--timeout",
    "-t",
    default=300,
    type=int,
    help="Timeout in seconds when using --wait (default: 300).",
)
def trigger(
    workflow_id: str,
    data_json: str | None,
    file_path: Path | None,
    wait_for_completion: bool,
    timeout: int,
) -> None:
    """Trigger workflow execution.

    Executes a workflow by ID and optionally waits for completion.
    Returns the execution ID immediately, or the full execution result
    if --wait is specified.

    Examples:

        n8n-cli trigger 123

        n8n-cli trigger 123 --data '{"key": "value"}'

        n8n-cli trigger 123 --file input.json

        n8n-cli trigger 123 --wait --timeout 60
    """
    # Validate mutual exclusivity
    if data_json and file_path:
        console.print("[red]Error:[/red] Cannot use both --data and --file")
        raise SystemExit(1)

    # Parse input data
    input_data: dict[str, Any] | None = None

    if data_json:
        try:
            parsed = json.loads(data_json)
            if not isinstance(parsed, dict):
                console.print(
                    "[red]Error:[/red] Invalid JSON data - must be an object, "
                    "not a list or primitive"
                )
                raise SystemExit(1)
            input_data = parsed
        except json.JSONDecodeError as e:
            console.print(
                f"[red]Error:[/red] Invalid JSON data - {e.msg} "
                f"at line {e.lineno}, column {e.colno}"
            )
            raise SystemExit(1) from None

    if file_path:
        try:
            json_content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            console.print(f"[red]Error:[/red] Failed to read file: {e}")
            raise SystemExit(1) from None

        try:
            parsed = json.loads(json_content)
            if not isinstance(parsed, dict):
                console.print(
                    "[red]Error:[/red] Invalid JSON in file - must be an object, "
                    "not a list or primitive"
                )
                raise SystemExit(1)
            input_data = parsed
        except json.JSONDecodeError as e:
            console.print(
                f"[red]Error:[/red] Invalid JSON in file - {e.msg} "
                f"at line {e.lineno}, column {e.colno}"
            )
            raise SystemExit(1) from None

    # Load config
    try:
        config = require_config()
    except ConfigurationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from None

    assert config.api_url is not None
    assert config.api_key is not None

    # Execute workflow
    try:
        result = asyncio.run(
            _trigger_workflow(
                config.api_url,
                config.api_key,
                workflow_id,
                input_data,
                wait_for_completion,
                timeout,
            )
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error:[/red] Workflow not found: {workflow_id}")
        elif e.response.status_code == 400:
            # Try to extract error message
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except (json.JSONDecodeError, KeyError):
                error_msg = str(e)
            # Check if it's an inactive workflow error
            if "active" in error_msg.lower() or "inactive" in error_msg.lower():
                console.print(
                    f"[red]Error:[/red] Workflow is not active. "
                    f"Enable with: n8n-cli update {workflow_id} --activate"
                )
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
        else:
            console.print(f"[red]Error:[/red] API error: {e.response.status_code}")
        raise SystemExit(1) from None
    except TimeoutError:
        console.print(
            f"[red]Error:[/red] Execution timed out after {timeout} seconds"
        )
        raise SystemExit(1) from None

    # Output result
    click.echo(json.dumps(result, indent=2))


async def _trigger_workflow(
    api_url: str,
    api_key: str,
    workflow_id: str,
    data: dict[str, Any] | None,
    wait_for_completion: bool,
    timeout: int,
) -> dict[str, Any]:
    """Trigger a workflow and optionally wait for completion.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID to execute.
        data: Optional input data.
        wait_for_completion: Whether to poll for completion.
        timeout: Timeout in seconds for waiting.

    Returns:
        Execution info (immediate) or full execution result (if waiting).

    Raises:
        TimeoutError: If execution does not complete within timeout.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        # Execute the workflow
        exec_result = await client.execute_workflow(workflow_id, data)
        execution_id = exec_result.get("executionId")

        if not wait_for_completion or not execution_id:
            return exec_result

        # Poll for completion
        start_time = time.monotonic()
        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Execution did not complete within {timeout}s")

            execution = await client.get_execution(str(execution_id))
            status = execution.get("status", "").lower()

            if status in TERMINAL_STATUSES:
                return execution

            await asyncio.sleep(POLL_INTERVAL)
