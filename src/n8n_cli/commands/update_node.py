"""Update node command for n8n-cli."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click

from n8n_cli.client import N8nClient
from n8n_cli.config import require_config
from n8n_cli.exceptions import NotFoundError, ValidationError
from n8n_cli.output import format_datetime, get_formatter_from_context


def find_node(
    nodes: list[dict[str, Any]],
    node_name: str | None,
    node_id: str | None,
) -> dict[str, Any] | None:
    """Find a node by name or ID.

    Args:
        nodes: List of node dictionaries from the workflow.
        node_name: Name of the node to find.
        node_id: ID of the node to find.

    Returns:
        The matching node dictionary, or None if not found.
    """
    for node in nodes:
        if node_name and node.get("name") == node_name:
            return node
        if node_id and node.get("id") == node_id:
            return node
    return None


def parse_value(value_str: str) -> Any:
    """Parse a value string, auto-detecting JSON types.

    Attempts to parse as JSON first (handles numbers, booleans, arrays, objects).
    If JSON parsing fails, treats the value as a plain string.

    Args:
        value_str: The string value to parse.

    Returns:
        The parsed value (could be str, int, float, bool, list, dict, or None).
    """
    try:
        return json.loads(value_str)
    except json.JSONDecodeError:
        return value_str


def set_nested_param(params: dict[str, Any], path: str, value: Any) -> None:
    """Set a nested parameter using dot notation.

    Creates intermediate dictionaries if they don't exist.

    Args:
        params: The parameters dictionary to update.
        path: Dot-notation path (e.g., "options.timeout").
        value: The value to set.

    Example:
        set_nested_param(params, "options.timeout", 30)
        # Results in: params["options"]["timeout"] = 30
    """
    keys = path.split(".")
    current = params
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            # Overwrite non-dict intermediate values
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


@click.command("update-node")
@click.argument("workflow_id")
@click.option(
    "--node-name",
    "-n",
    "node_name",
    help="Name of the node to update.",
)
@click.option(
    "--node-id",
    "-i",
    "node_id",
    help="ID of the node to update.",
)
@click.option(
    "--param",
    "-p",
    "param_path",
    required=True,
    help="Parameter path to update (supports dot notation for nested params).",
)
@click.option(
    "--value",
    "-v",
    "value_str",
    required=True,
    help="New value (JSON auto-detected; otherwise treated as string).",
)
@click.pass_context
def update_node(
    ctx: click.Context,
    workflow_id: str,
    node_name: str | None,
    node_id: str | None,
    param_path: str,
    value_str: str,
) -> None:
    """Update a specific parameter on a node within a workflow.

    Allows targeted updates to individual node parameters without handling
    the full workflow JSON. Fetches the workflow, updates the specified
    parameter on the target node, and pushes the change back to n8n.

    Examples:

        n8n-cli update-node abc123 --node-name "HTTP Request" --param "url" --value "https://api.example.com"

        n8n-cli update-node abc123 --node-id "xyz789" --param "method" --value "POST"

        n8n-cli update-node abc123 -n "HTTP Request" -p "options.timeout" -v "30000"

        n8n-cli update-node abc123 -n "Set" -p "values" -v '{"key": "value"}'
    """
    formatter = get_formatter_from_context(ctx)

    # Validate: must provide exactly one of --node-name or --node-id
    if node_name and node_id:
        raise ValidationError("Cannot use both --node-name and --node-id")
    if not node_name and not node_id:
        raise ValidationError("Must specify either --node-name or --node-id")

    # Load config (raises ConfigError if not configured)
    config = require_config()

    assert config.api_url is not None
    assert config.api_key is not None

    # Parse value
    parsed_value = parse_value(value_str)

    # Execute update
    result = asyncio.run(
        _update_node(
            api_url=config.api_url,
            api_key=config.api_key,
            workflow_id=workflow_id,
            node_name=node_name,
            node_id=node_id,
            param_path=param_path,
            value=parsed_value,
        )
    )

    # Output updated workflow
    formatter.output_dict(
        result,
        fields=["id", "name", "active", "updatedAt"],
        labels={
            "id": "ID",
            "name": "Name",
            "active": "Active",
            "updatedAt": "Updated",
        },
        formatters={
            "updatedAt": format_datetime,
        },
    )


# Fields that the n8n API accepts for workflow updates (whitelist approach)
# All other fields returned by GET are read-only and will cause 400 errors
WRITABLE_WORKFLOW_FIELDS = {
    "name",
    "nodes",
    "connections",
    "settings",
    "staticData",
    "pinData",
    "active",
}


def extract_writable_fields(workflow: dict[str, Any]) -> dict[str, Any]:
    """Extract only the fields that n8n API accepts for workflow updates.

    Args:
        workflow: The workflow dictionary from GET response.

    Returns:
        A new dictionary with only writable fields.
    """
    return {k: v for k, v in workflow.items() if k in WRITABLE_WORKFLOW_FIELDS}


async def _update_node(
    api_url: str,
    api_key: str,
    workflow_id: str,
    node_name: str | None,
    node_id: str | None,
    param_path: str,
    value: Any,
) -> dict[str, Any]:
    """Update a specific node parameter in a workflow.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.
        workflow_id: The workflow ID containing the node.
        node_name: Name of the node to update (if using name lookup).
        node_id: ID of the node to update (if using ID lookup).
        param_path: Dot-notation path to the parameter.
        value: The new value to set.

    Returns:
        Updated workflow.

    Raises:
        NotFoundError: If workflow or node not found.
    """
    async with N8nClient(base_url=api_url, api_key=api_key) as client:
        # Fetch workflow
        workflow = await client.get_workflow(workflow_id)

        # Find target node
        nodes = workflow.get("nodes", [])
        node = find_node(nodes, node_name, node_id)

        if node is None:
            identifier = node_name or node_id
            raise NotFoundError(f"Node not found: {identifier}")

        # Ensure parameters dict exists
        if "parameters" not in node:
            node["parameters"] = {}

        # Update the parameter
        set_nested_param(node["parameters"], param_path, value)

        # Extract only writable fields before sending update
        workflow_payload = extract_writable_fields(workflow)

        # Push updated workflow
        return await client.update_workflow(workflow_id, workflow_payload)
