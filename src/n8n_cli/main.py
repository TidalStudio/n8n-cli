"""CLI entry point for n8n-cli."""

import sys
import traceback

import click

from n8n_cli import __version__
from n8n_cli.commands.configure import configure
from n8n_cli.commands.create import create
from n8n_cli.commands.delete import delete
from n8n_cli.commands.disable import disable
from n8n_cli.commands.enable import enable
from n8n_cli.commands.execution import execution
from n8n_cli.commands.executions import executions
from n8n_cli.commands.trigger import trigger
from n8n_cli.commands.update import update
from n8n_cli.commands.workflow import workflow
from n8n_cli.commands.workflows import workflows
from n8n_cli.exceptions import N8nCliError
from n8n_cli.output import get_formatter


class ExceptionHandlingGroup(click.Group):
    """Click group that handles N8nCliError exceptions globally."""

    def invoke(self, ctx: click.Context) -> None:
        """Invoke the command with exception handling."""
        try:
            super().invoke(ctx)
        except N8nCliError as e:
            debug = ctx.obj.get("debug", False) if ctx.obj else False
            no_color = ctx.obj.get("no_color", False) if ctx.obj else False
            formatter = get_formatter(no_color=no_color)

            if debug:
                formatter.output_error(f"{e.message}\n")
                traceback.print_exc(file=sys.stderr)
            else:
                formatter.output_error(e.message)

            sys.exit(e.exit_code)


@click.group(cls=ExceptionHandlingGroup, invoke_without_command=True)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "table"], case_sensitive=False),
    default=None,
    envvar="N8N_CLI_FORMAT",
    help="Output format (default: json)",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="Disable colored output",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    envvar="N8N_CLI_DEBUG",
    help="Show full stack traces on errors",
)
@click.version_option(version=__version__, prog_name="n8n-cli")
@click.pass_context
def cli(ctx: click.Context, output_format: str | None, no_color: bool, debug: bool) -> None:
    """n8n CLI - A command-line interface for interacting with n8n."""
    ctx.ensure_object(dict)
    ctx.obj["output_format"] = output_format or "json"
    ctx.obj["no_color"] = no_color
    ctx.obj["debug"] = debug
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register commands
cli.add_command(configure)
cli.add_command(create)
cli.add_command(delete)
cli.add_command(disable)
cli.add_command(enable)
cli.add_command(execution)
cli.add_command(executions)
cli.add_command(trigger)
cli.add_command(update)
cli.add_command(workflow)
cli.add_command(workflows)


if __name__ == "__main__":
    cli()
