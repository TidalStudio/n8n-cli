"""Output formatting utilities for n8n-cli."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table


class OutputFormat(Enum):
    """Output format options."""

    JSON = "json"
    TABLE = "table"


# Status colors for executions
STATUS_COLORS: dict[str, str] = {
    "success": "green",
    "error": "red",
    "running": "yellow",
    "waiting": "blue",
    "canceled": "dim",
}


def format_datetime(value: str | None) -> str:
    """Format ISO datetime string to human-readable format.

    Args:
        value: ISO datetime string or None.

    Returns:
        Formatted datetime string or empty string if None.
    """
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return str(value)


def format_boolean(value: bool) -> str:
    """Format boolean as checkmark or X.

    Args:
        value: Boolean value.

    Returns:
        Checkmark for True, X for False.
    """
    return "✓" if value else "✗"


def truncate(value: str, max_length: int = 50) -> str:
    """Truncate string with ellipsis if too long.

    Args:
        value: String to truncate.
        max_length: Maximum length before truncation.

    Returns:
        Truncated string with ellipsis or original string.
    """
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


class OutputFormatter:
    """Handles output formatting for CLI commands."""

    def __init__(self, output_format: OutputFormat, no_color: bool = False) -> None:
        """Initialize the output formatter.

        Args:
            output_format: The format to use for output.
            no_color: Whether to disable colored output.
        """
        self.format = output_format
        self.no_color = no_color
        # Let Rich auto-detect terminal; only force no_color if explicitly requested
        self.console = Console(no_color=no_color)

    def output_list(
        self,
        data: list[dict[str, Any]],
        columns: list[str],
        headers: list[str] | None = None,
        formatters: dict[str, Any] | None = None,
    ) -> None:
        """Output a list of items as JSON or table.

        Args:
            data: List of dictionaries to output.
            columns: List of column keys to display.
            headers: Optional list of header names (defaults to column keys).
            formatters: Optional dict of column -> formatter function.
        """
        if self.format == OutputFormat.JSON:
            print(json.dumps(data, indent=2))
            return

        if headers is None:
            headers = columns

        if formatters is None:
            formatters = {}

        table = Table(box=box.ROUNDED)

        for header in headers:
            table.add_column(header)

        for item in data:
            row = []
            for col in columns:
                value = item.get(col, "")
                if col in formatters:
                    value = formatters[col](value)
                elif isinstance(value, bool):
                    value = format_boolean(value)
                elif value is None:
                    value = ""
                else:
                    value = str(value)
                row.append(value)
            table.add_row(*row)

        self.console.print(table)

    def output_dict(
        self,
        data: dict[str, Any],
        fields: list[str] | None = None,
        labels: dict[str, str] | None = None,
        formatters: dict[str, Any] | None = None,
    ) -> None:
        """Output a single item as JSON or key-value table.

        Args:
            data: Dictionary to output.
            fields: Optional list of fields to display (defaults to all).
            labels: Optional dict mapping field names to display labels.
            formatters: Optional dict of field -> formatter function.
        """
        if self.format == OutputFormat.JSON:
            print(json.dumps(data, indent=2))
            return

        if fields is None:
            fields = list(data.keys())

        if labels is None:
            labels = {}

        if formatters is None:
            formatters = {}

        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")

        for field in fields:
            if field not in data:
                continue
            label = labels.get(field, field)
            value = data[field]
            if field in formatters:
                value = formatters[field](value)
            elif isinstance(value, bool):
                value = format_boolean(value)
            elif isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            elif value is None:
                value = ""
            else:
                value = str(value)
            table.add_row(label, value)

        self.console.print(table)

    def output_error(self, message: str) -> None:
        """Output an error message.

        Args:
            message: The error message to display.
        """
        self.console.print(f"[red]Error:[/red] {message}")

    def output_success(self, message: str) -> None:
        """Output a success message.

        Args:
            message: The success message to display.
        """
        self.console.print(f"[green]{message}[/green]")


def get_formatter(
    output_format: str | None = None, no_color: bool = False
) -> OutputFormatter:
    """Create an OutputFormatter from string format name.

    Args:
        output_format: Format name ("json" or "table"), defaults to "json".
        no_color: Whether to disable colored output.

    Returns:
        Configured OutputFormatter instance.
    """
    fmt = OutputFormat.JSON
    if output_format == "table":
        fmt = OutputFormat.TABLE
    return OutputFormatter(fmt, no_color=no_color)


def get_formatter_from_context(ctx: Any) -> OutputFormatter:
    """Create an OutputFormatter from Click context.

    Safely handles cases where ctx.obj is None (e.g., direct command invocation).

    Args:
        ctx: Click context object.

    Returns:
        Configured OutputFormatter instance.
    """
    obj = ctx.obj if ctx.obj is not None else {}
    return get_formatter(obj.get("output_format"), obj.get("no_color", False))
