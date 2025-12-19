"""CLI entry point for n8n-cli."""

import click

from n8n_cli import __version__
from n8n_cli.commands.configure import configure
from n8n_cli.commands.create import create
from n8n_cli.commands.delete import delete
from n8n_cli.commands.execution import execution
from n8n_cli.commands.executions import executions
from n8n_cli.commands.trigger import trigger
from n8n_cli.commands.update import update
from n8n_cli.commands.workflow import workflow
from n8n_cli.commands.workflows import workflows


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="n8n-cli")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """n8n CLI - A command-line interface for interacting with n8n."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register commands
cli.add_command(configure)
cli.add_command(create)
cli.add_command(delete)
cli.add_command(execution)
cli.add_command(executions)
cli.add_command(trigger)
cli.add_command(update)
cli.add_command(workflow)
cli.add_command(workflows)


if __name__ == "__main__":
    cli()
