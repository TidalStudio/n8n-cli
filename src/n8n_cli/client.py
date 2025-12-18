"""HTTP client for interacting with the n8n API."""

from types import TracebackType
from typing import Self

import httpx


class N8nClient:
    """Async HTTP client for the n8n API.

    Args:
        base_url: The base URL of the n8n instance (e.g., "http://localhost:5678").
        api_key: Optional API key for authentication.
        timeout: Request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._build_headers(),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_headers(self) -> dict[str, str]:
        """Build request headers including authentication if configured."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the underlying HTTP client.

        Raises:
            RuntimeError: If accessed outside of async context manager.
        """
        if self._client is None:
            msg = "Client must be used within an async context manager"
            raise RuntimeError(msg)
        return self._client

    async def health_check(self) -> bool:
        """Check if the n8n instance is reachable.

        Returns:
            True if the instance is healthy, False otherwise.
        """
        try:
            response = await self.client.get("/healthz")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
