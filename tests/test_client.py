"""Tests for the HTTP client."""

import pytest

from n8n_cli.client import N8nClient


def test_client_init() -> None:
    """Test client initialization with required parameters."""
    client = N8nClient(base_url="http://localhost:5678")
    assert client.base_url == "http://localhost:5678"
    assert client.api_key is None
    assert client.timeout == 30.0


def test_client_init_with_api_key() -> None:
    """Test client initialization with API key."""
    client = N8nClient(
        base_url="http://localhost:5678",
        api_key="test-api-key",
    )
    assert client.api_key == "test-api-key"


def test_client_init_strips_trailing_slash() -> None:
    """Test that trailing slashes are stripped from base_url."""
    client = N8nClient(base_url="http://localhost:5678/")
    assert client.base_url == "http://localhost:5678"


def test_client_init_custom_timeout() -> None:
    """Test client initialization with custom timeout."""
    client = N8nClient(base_url="http://localhost:5678", timeout=60.0)
    assert client.timeout == 60.0


def test_build_headers_without_api_key() -> None:
    """Test header building without API key."""
    client = N8nClient(base_url="http://localhost:5678")
    headers = client._build_headers()
    assert headers == {"Content-Type": "application/json"}
    assert "X-N8N-API-KEY" not in headers


def test_build_headers_with_api_key() -> None:
    """Test header building with API key."""
    client = N8nClient(
        base_url="http://localhost:5678",
        api_key="test-key",
    )
    headers = client._build_headers()
    assert headers["X-N8N-API-KEY"] == "test-key"
    assert headers["Content-Type"] == "application/json"


def test_client_property_raises_outside_context() -> None:
    """Test that accessing client outside context manager raises error."""
    n8n = N8nClient(base_url="http://localhost:5678")
    with pytest.raises(RuntimeError, match="async context manager"):
        _ = n8n.client


@pytest.mark.asyncio
async def test_client_context_manager() -> None:
    """Test async context manager lifecycle."""
    async with N8nClient(base_url="http://localhost:5678") as client:
        assert client._client is not None
    assert client._client is None
