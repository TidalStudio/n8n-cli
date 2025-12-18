"""Tests for configure command."""

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from n8n_cli.commands.configure import configure
from n8n_cli.main import cli


@pytest.fixture
def cli_runner():
    """Provide isolated CLI runner."""
    return CliRunner()


class TestConfigureCommand:
    """Tests for configure command."""

    def test_configure_non_interactive_success(self, cli_runner, tmp_path):
        """Test non-interactive configure with flags."""
        config_file = tmp_path / ".env"

        with (
            patch("n8n_cli.config.get_config_path", return_value=config_file),
            patch(
                "n8n_cli.commands.configure._test_connection",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            result = cli_runner.invoke(
                configure, ["--url", "http://localhost:5678", "--api-key", "test-key"]
            )

        assert result.exit_code == 0
        assert "Configuration saved" in result.output
        assert config_file.exists()

    def test_configure_interactive_prompts(self, cli_runner, tmp_path):
        """Test interactive mode prompts for input."""
        config_file = tmp_path / ".env"

        with (
            patch("n8n_cli.config.get_config_path", return_value=config_file),
            patch(
                "n8n_cli.commands.configure._test_connection",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            result = cli_runner.invoke(
                configure, input="http://localhost:5678\ntest-api-key\n"
            )

        assert result.exit_code == 0
        assert config_file.exists()

    def test_configure_connection_failure_warns_but_saves(self, cli_runner, tmp_path):
        """Test that connection failure warns but still saves config."""
        config_file = tmp_path / ".env"

        with (
            patch("n8n_cli.config.get_config_path", return_value=config_file),
            patch(
                "n8n_cli.commands.configure._test_connection",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            result = cli_runner.invoke(
                configure, ["--url", "http://bad-url", "--api-key", "key"]
            )

        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "Could not connect" in result.output
        assert config_file.exists()  # Still saved

    def test_configure_shows_existing_defaults(self, cli_runner, tmp_path):
        """Test that existing config values are shown as defaults."""
        config_file = tmp_path / ".env"
        config_file.write_text("N8N_API_URL=http://existing\nN8N_API_KEY=existing-key")

        with (
            patch("n8n_cli.config.get_config_path", return_value=config_file),
            patch(
                "n8n_cli.commands.configure._test_connection",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            # Just press enter to accept defaults
            result = cli_runner.invoke(configure, input="\n\n")

        assert result.exit_code == 0
        assert "http://existing" in result.output

    def test_configure_registered_with_cli(self, cli_runner):
        """Test configure command is registered with main CLI."""
        result = cli_runner.invoke(cli, ["--help"])
        assert "configure" in result.output

    def test_configure_help_text(self, cli_runner):
        """Test configure --help shows usage."""
        result = cli_runner.invoke(configure, ["--help"])
        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--api-key" in result.output

    def test_configure_normalizes_url(self, cli_runner, tmp_path):
        """Test URL trailing slash is removed."""
        config_file = tmp_path / ".env"

        with (
            patch("n8n_cli.config.get_config_path", return_value=config_file),
            patch(
                "n8n_cli.commands.configure._test_connection",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            result = cli_runner.invoke(
                configure, ["--url", "http://localhost:5678/", "--api-key", "key"]
            )

        assert result.exit_code == 0
        content = config_file.read_text()
        assert "N8N_API_URL=http://localhost:5678\n" in content  # No trailing slash


class TestConnectionTest:
    """Tests for _test_connection helper."""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test _test_connection returns True on success."""
        from n8n_cli.commands.configure import _test_connection

        with patch(
            "n8n_cli.client.N8nClient.health_check", new_callable=AsyncMock
        ) as mock_health:
            mock_health.return_value = True
            result = await _test_connection("http://test", "key")
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test _test_connection returns False on failure."""
        from n8n_cli.commands.configure import _test_connection

        with patch(
            "n8n_cli.client.N8nClient.health_check", new_callable=AsyncMock
        ) as mock_health:
            mock_health.return_value = False
            result = await _test_connection("http://bad", "key")
            assert result is False
