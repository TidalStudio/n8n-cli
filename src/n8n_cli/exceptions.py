"""Custom exceptions for n8n-cli with exit codes and helpful messages."""

from __future__ import annotations


class N8nCliError(Exception):
    """Base exception for n8n-cli errors.

    Attributes:
        exit_code: The exit code to return when this exception is raised.
        message: The error message to display.
    """

    exit_code: int = 1

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ConfigError(N8nCliError):
    """Configuration is missing or invalid.

    Exit code 2 indicates a configuration problem that the user needs to fix
    before the CLI can function.
    """

    exit_code = 2


class ConnectionError(N8nCliError):
    """Cannot connect to the n8n server.

    This includes DNS failures, connection refused, and other network issues.
    """

    pass


class AuthenticationError(N8nCliError):
    """API key is invalid or expired (HTTP 401)."""

    pass


class NotFoundError(N8nCliError):
    """Requested resource was not found (HTTP 404)."""

    pass


class ValidationError(N8nCliError):
    """Request validation failed (HTTP 400).

    This includes invalid JSON, missing required fields, and other
    client-side errors.
    """

    pass


class TimeoutError(N8nCliError):
    """Request or operation timed out."""

    pass


class ApiError(N8nCliError):
    """Generic API error with HTTP status code.

    Used for unexpected HTTP errors that don't fit other categories.
    """

    def __init__(self, message: str, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(message)
