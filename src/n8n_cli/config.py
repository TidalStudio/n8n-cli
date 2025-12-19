"""Configuration management for n8n-cli."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from n8n_cli.exceptions import ConfigError

# Constants
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "n8n-cli"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / ".env"
ENV_API_URL = "N8N_API_URL"
ENV_API_KEY = "N8N_API_KEY"


# Backward compatibility alias
ConfigurationError = ConfigError


@dataclass
class Config:
    """Configuration data class."""

    api_url: str | None = None
    api_key: str | None = None

    def is_configured(self) -> bool:
        """Check if minimum required configuration is present."""
        return self.api_url is not None and self.api_key is not None


def get_config_path() -> Path:
    """Get the configuration file path."""
    return DEFAULT_CONFIG_FILE


def load_config() -> Config:
    """Load configuration with priority: env vars > config file.

    Returns:
        Config object with loaded values.
    """
    # Start with file-based config
    file_config = _load_from_file()

    # Override with environment variables
    api_url = os.environ.get(ENV_API_URL) or file_config.get("api_url")
    api_key = os.environ.get(ENV_API_KEY) or file_config.get("api_key")

    return Config(api_url=api_url, api_key=api_key)


def _load_from_file() -> dict[str, str | None]:
    """Load configuration from .env file.

    Returns:
        Dictionary with config values (may be empty).
    """
    config_path = get_config_path()
    result: dict[str, str | None] = {"api_url": None, "api_key": None}

    if not config_path.exists():
        return result

    # Parse .env file (simple KEY=value format)
    for line in config_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key == ENV_API_URL:
                result["api_url"] = value
            elif key == ENV_API_KEY:
                result["api_key"] = value

    return result


def save_config(api_url: str, api_key: str) -> Path:
    """Save configuration to .env file with secure permissions.

    Args:
        api_url: The n8n instance URL.
        api_key: The API key for authentication.

    Returns:
        Path to the saved configuration file.
    """
    config_path = get_config_path()

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Build .env content
    content = f"""{ENV_API_URL}={api_url}
{ENV_API_KEY}={api_key}
"""

    # Write file
    config_path.write_text(content)

    # Set secure permissions (600 = owner read/write only)
    _set_secure_permissions(config_path)

    return config_path


def _set_secure_permissions(path: Path) -> None:
    """Set secure file permissions (cross-platform).

    On Unix: chmod 600
    On Windows: Best-effort (Windows handles permissions differently)
    """
    import contextlib

    with contextlib.suppress(OSError):
        # Unix-like systems
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600


def require_config() -> Config:
    """Load config and raise if not configured.

    Returns:
        Valid Config object.

    Raises:
        ConfigError: If required configuration is missing.
    """
    config = load_config()
    if not config.is_configured():
        raise ConfigError(
            "n8n-cli is not configured. Run 'n8n-cli configure' to set up credentials, "
            f"or set {ENV_API_URL} and {ENV_API_KEY} environment variables."
        )
    return config
