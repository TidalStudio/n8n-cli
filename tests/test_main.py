"""Tests for the CLI entry point."""

from click.testing import CliRunner

from n8n_cli import __version__
from n8n_cli.main import cli


def test_cli_help(cli_runner: CliRunner) -> None:
    """Test that --help shows help text."""
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "n8n CLI" in result.output
    assert "command-line interface" in result.output.lower()


def test_cli_version(cli_runner: CliRunner) -> None:
    """Test that --version shows the correct version."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output
    assert "n8n-cli" in result.output


def test_cli_no_args_shows_help(cli_runner: CliRunner) -> None:
    """Test that running without arguments shows help."""
    result = cli_runner.invoke(cli)
    assert result.exit_code == 0
    assert "n8n CLI" in result.output
