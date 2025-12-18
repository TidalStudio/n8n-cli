"""Tests for configuration management."""

from unittest.mock import patch

import pytest

from n8n_cli.config import (
    ENV_API_KEY,
    ENV_API_URL,
    Config,
    ConfigurationError,
    load_config,
    require_config,
    save_config,
)


class TestConfig:
    """Tests for Config dataclass."""

    def test_config_defaults(self):
        """Test Config has None defaults."""
        config = Config()
        assert config.api_url is None
        assert config.api_key is None

    def test_config_is_configured_false_when_empty(self):
        """Test is_configured returns False when values missing."""
        assert Config().is_configured() is False
        assert Config(api_url="http://test").is_configured() is False
        assert Config(api_key="key").is_configured() is False

    def test_config_is_configured_true_when_complete(self):
        """Test is_configured returns True when both values present."""
        config = Config(api_url="http://test", api_key="key")
        assert config.is_configured() is True


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_from_env_vars(self, monkeypatch, tmp_path):
        """Test environment variables are loaded."""
        # Ensure no file config interferes
        nonexistent = tmp_path / "nonexistent" / ".env"
        with patch("n8n_cli.config.get_config_path", return_value=nonexistent):
            monkeypatch.setenv(ENV_API_URL, "http://env-url")
            monkeypatch.setenv(ENV_API_KEY, "env-key")

            config = load_config()
            assert config.api_url == "http://env-url"
            assert config.api_key == "env-key"

    def test_load_config_from_file(self, tmp_path, monkeypatch):
        """Test config file is loaded when no env vars."""
        # Clear env vars
        monkeypatch.delenv(ENV_API_URL, raising=False)
        monkeypatch.delenv(ENV_API_KEY, raising=False)

        # Setup file config
        config_file = tmp_path / ".env"
        config_file.write_text(f"{ENV_API_URL}=http://file-url\n{ENV_API_KEY}=file-key")

        with patch("n8n_cli.config.get_config_path", return_value=config_file):
            config = load_config()
            assert config.api_url == "http://file-url"
            assert config.api_key == "file-key"

    def test_env_vars_override_file(self, tmp_path, monkeypatch):
        """Test environment variables take priority over file."""
        # Setup file config
        config_file = tmp_path / ".env"
        config_file.write_text(f"{ENV_API_URL}=http://file-url\n{ENV_API_KEY}=file-key")

        with patch("n8n_cli.config.get_config_path", return_value=config_file):
            # Set env var for URL only
            monkeypatch.setenv(ENV_API_URL, "http://env-url")
            monkeypatch.delenv(ENV_API_KEY, raising=False)

            config = load_config()
            assert config.api_url == "http://env-url"  # From env
            assert config.api_key == "file-key"  # From file

    def test_load_config_empty_when_no_config(self, tmp_path, monkeypatch):
        """Test loading returns empty config when nothing configured."""
        # Clear env vars
        monkeypatch.delenv(ENV_API_URL, raising=False)
        monkeypatch.delenv(ENV_API_KEY, raising=False)

        nonexistent = tmp_path / "nonexistent" / ".env"

        with patch("n8n_cli.config.get_config_path", return_value=nonexistent):
            config = load_config()
            assert config.api_url is None
            assert config.api_key is None

    def test_load_config_handles_comments_and_empty_lines(self, tmp_path, monkeypatch):
        """Test .env parser handles comments and empty lines."""
        monkeypatch.delenv(ENV_API_URL, raising=False)
        monkeypatch.delenv(ENV_API_KEY, raising=False)

        config_file = tmp_path / ".env"
        config_file.write_text(
            f"# This is a comment\n\n{ENV_API_URL}=http://test\n# Another comment\n{ENV_API_KEY}=key"
        )

        with patch("n8n_cli.config.get_config_path", return_value=config_file):
            config = load_config()
            assert config.api_url == "http://test"
            assert config.api_key == "key"

    def test_load_config_strips_quotes(self, tmp_path, monkeypatch):
        """Test .env parser strips quotes from values."""
        monkeypatch.delenv(ENV_API_URL, raising=False)
        monkeypatch.delenv(ENV_API_KEY, raising=False)

        config_file = tmp_path / ".env"
        config_file.write_text(f'{ENV_API_URL}="http://test"\n{ENV_API_KEY}=\'my-key\'')

        with patch("n8n_cli.config.get_config_path", return_value=config_file):
            config = load_config()
            assert config.api_url == "http://test"
            assert config.api_key == "my-key"


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_file(self, tmp_path):
        """Test save_config creates .env file."""
        config_file = tmp_path / ".config" / "n8n-cli" / ".env"

        with patch("n8n_cli.config.get_config_path", return_value=config_file):
            result = save_config("http://test", "test-key")

            assert result == config_file
            assert config_file.exists()
            content = config_file.read_text()
            assert "N8N_API_URL=http://test" in content
            assert "N8N_API_KEY=test-key" in content

    def test_save_config_creates_directory(self, tmp_path):
        """Test save_config creates parent directories."""
        config_file = tmp_path / "deep" / "nested" / ".env"

        with patch("n8n_cli.config.get_config_path", return_value=config_file):
            save_config("http://test", "key")
            assert config_file.parent.exists()

    def test_save_config_overwrites_existing(self, tmp_path):
        """Test save_config overwrites existing file."""
        config_file = tmp_path / ".env"
        config_file.write_text("OLD_CONTENT=value")

        with patch("n8n_cli.config.get_config_path", return_value=config_file):
            save_config("http://new", "new-key")

            content = config_file.read_text()
            assert "OLD_CONTENT" not in content
            assert "N8N_API_URL=http://new" in content


class TestRequireConfig:
    """Tests for require_config function."""

    def test_require_config_raises_when_not_configured(self, tmp_path, monkeypatch):
        """Test require_config raises ConfigurationError when not configured."""
        monkeypatch.delenv(ENV_API_URL, raising=False)
        monkeypatch.delenv(ENV_API_KEY, raising=False)

        nonexistent = tmp_path / ".env"

        with patch("n8n_cli.config.get_config_path", return_value=nonexistent):
            with pytest.raises(ConfigurationError) as exc_info:
                require_config()

            assert "not configured" in str(exc_info.value)
            assert "n8n-cli configure" in str(exc_info.value)

    def test_require_config_returns_config_when_valid(self, monkeypatch, tmp_path):
        """Test require_config returns config when valid."""
        nonexistent = tmp_path / "nonexistent" / ".env"
        with patch("n8n_cli.config.get_config_path", return_value=nonexistent):
            monkeypatch.setenv(ENV_API_URL, "http://test")
            monkeypatch.setenv(ENV_API_KEY, "key")

            config = require_config()
            assert config.api_url == "http://test"
            assert config.api_key == "key"
