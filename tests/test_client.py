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


class TestGetWorkflow:
    """Tests for N8nClient.get_workflow method."""

    @pytest.mark.asyncio
    async def test_get_workflow_returns_workflow(self) -> None:
        """Test get_workflow returns full workflow definition."""
        from typing import Any
        from unittest.mock import AsyncMock, MagicMock

        sample_workflow: dict[str, Any] = {
            "id": "1",
            "name": "Test Workflow",
            "active": True,
            "nodes": [{"id": "node1", "name": "Start"}],
            "connections": {},
            "settings": {},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = sample_workflow
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.get_workflow("1")

        assert result["id"] == "1"
        assert result["name"] == "Test Workflow"
        assert "nodes" in result
        assert "connections" in result

    @pytest.mark.asyncio
    async def test_get_workflow_calls_correct_endpoint(self) -> None:
        """Test get_workflow calls the correct API endpoint."""
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "abc123"}
        mock_response.raise_for_status = MagicMock()

        async with N8nClient(base_url="http://test", api_key="key") as client:
            mock_get = AsyncMock(return_value=mock_response)
            client._client.get = mock_get
            await client.get_workflow("abc123")
            mock_get.assert_called_once_with("/api/v1/workflows/abc123")

    @pytest.mark.asyncio
    async def test_get_workflow_raises_on_404(self) -> None:
        """Test get_workflow raises HTTPStatusError on 404."""
        from unittest.mock import AsyncMock, MagicMock

        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404),
        )

        async with N8nClient(base_url="http://test", api_key="key") as client:
            client._client.get = AsyncMock(return_value=mock_response)
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_workflow("999")
