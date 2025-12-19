"""Trigger workflow command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import click

from n8n_cli.client import N8nClient
from n8n_cli.config import require_config
from n8n_cli.exceptions import TimeoutError as CliTimeoutError
from n8n_cli.exceptions import ValidationError
from n8n_cli.output import STATUS_COLORS, format_datetime, get_formatter_from_context

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
@click.pass_context
def trigger(
    ctx: click.Context,
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
    formatter = get_formatter_from_context(ctx)

    # Validate mutual exclusivity
    if data_json and file_path:
        raise ValidationError("Cannot use both --data and --file")

    # Parse input data
    input_data: dict[str, Any] | None = None

    if data_json:
        try:
            parsed = json.loads(data_json)
            if not isinstance(parsed, dict):
                raise ValidationError(
                    "Invalid JSON data - must be an object, not a list or primitive"
                )
            input_data = parsed
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Invalid JSON data - {e.msg} at line {e.lineno}, column {e.colno}"
            ) from e

    if file_path:
        try:
            json_content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            raise ValidationError(f"Failed to read file: {e}") from e

        try:
            parsed = json.loads(json_content)
            if not isinstance(parsed, dict):
                raise ValidationError(
                    "Invalid JSON in file - must be an object, not a list or primitive"
                )
            input_data = parsed
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Invalid JSON in file - {e.msg} at line {e.lineno}, column {e.colno}"
            ) from e

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    # Execute workflow
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

    def format_status(s: str) -> str:
        """Format status with color."""
        color = STATUS_COLORS.get(s, "white")
        return f"[{color}]{s}[/{color}]"

    # Output result - different fields for immediate vs waited execution
    if wait_for_completion:
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
    else:
        formatter.output_dict(
            result,
            fields=["executionId"],
            labels={"executionId": "Execution ID"},
        )


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
                raise CliTimeoutError(f"Execution did not complete within {timeout}s")

            execution = await client.get_execution(str(execution_id))
            status = execution.get("status", "").lower()

            if status in TERMINAL_STATUSES:
                return execution

            await asyncio.sleep(POLL_INTERVAL)
