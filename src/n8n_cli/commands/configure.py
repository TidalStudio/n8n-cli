"""Configure command for n8n-cli."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.panel import Panel

from n8n_cli.client import N8nClient
from n8n_cli.config import load_config, save_config

console = Console()


@click.command()
@click.option(
    "--url",
    "api_url",
    help="n8n instance URL (e.g., http://localhost:5678)",
)
@click.option(
    "--api-key",
    "api_key",
    help="n8n API key for authentication",
)
def configure(api_url: str | None, api_key: str | None) -> None:
    """Configure n8n-cli with your n8n instance credentials.

    Run interactively to be prompted for values, or provide --url and --api-key
    flags for non-interactive CI/CD usage.

    Configuration is saved to ~/.config/n8n-cli/.env

    Environment variables N8N_API_URL and N8N_API_KEY will override
    saved configuration.
    """
    # Load existing config for defaults
    existing_config = load_config()

    # Determine if interactive mode (need to prompt for missing values)
    if api_url is None or api_key is None:
        console.print(
            Panel(
                "[bold]n8n-cli Configuration[/bold]\n\n"
                "Enter your n8n instance details below.\n"
                "Press Enter to keep existing values (shown in brackets).",
                title="Setup",
            )
        )

        # Prompt for API URL if not provided
        if api_url is None:
            default_url = existing_config.api_url or ""
            url_prompt = "n8n API URL"
            if default_url:
                url_prompt += f" [{default_url}]"

            api_url = click.prompt(
                url_prompt,
                default=default_url if default_url else None,
                show_default=False,
            )

        # Prompt for API Key if not provided (plain text as per user decision)
        if api_key is None:
            default_key = existing_config.api_key or ""
            key_prompt = "API Key"
            if default_key:
                # Show partial key for security hint
                if len(default_key) > 8:
                    masked = default_key[:4] + "..." + default_key[-4:]
                else:
                    masked = "****"
                key_prompt += f" [{masked}]"

            api_key = click.prompt(
                key_prompt,
                default=default_key if default_key else None,
                show_default=False,
                hide_input=False,  # Plain text as per user decision
            )

    # Validate inputs
    if not api_url:
        console.print("[red]Error:[/red] API URL is required")
        raise SystemExit(1)

    if not api_key:
        console.print("[red]Error:[/red] API key is required")
        raise SystemExit(1)

    # Normalize URL
    api_url = api_url.rstrip("/")

    # Test connection
    console.print("\n[dim]Testing connection...[/dim]")
    connection_ok = asyncio.run(_test_connection(api_url, api_key))

    if connection_ok:
        console.print("[green]Connection successful![/green]")
    else:
        # Warn but save anyway (per user decision)
        console.print(
            "[yellow]Warning:[/yellow] Could not connect to n8n instance. "
            "Configuration will be saved anyway.\n"
            "Please verify your URL and API key are correct."
        )

    # Save configuration
    config_path = save_config(api_url, api_key)
    console.print(f"\n[green]Configuration saved to:[/green] {config_path}")

    # Show summary
    masked_key = api_key[-4:] if len(api_key) > 4 else "****"
    console.print(
        Panel(
            f"[bold]API URL:[/bold] {api_url}\n"
            f"[bold]API Key:[/bold] {'*' * 8}...{masked_key}",
            title="Configuration Summary",
        )
    )


async def _test_connection(api_url: str, api_key: str) -> bool:
    """Test connection to n8n instance.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key.

    Returns:
        True if connection successful, False otherwise.
    """
    async with N8nClient(base_url=api_url, api_key=api_key, timeout=10.0) as client:
        return await client.health_check()
