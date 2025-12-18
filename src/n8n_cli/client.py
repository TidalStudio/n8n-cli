"""HTTP client for interacting with the n8n API."""

from types import TracebackType
from typing import Any, Self

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

    async def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Fetch a single workflow by ID.

        Args:
            workflow_id: The workflow ID (numeric or string).

        Returns:
            Full workflow definition including nodes and connections.

        Raises:
            httpx.HTTPStatusError: If workflow not found (404) or other API error.
        """
        response = await self.client.get(f"/api/v1/workflows/{workflow_id}")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def get_workflows(
        self,
        active: bool | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch workflows from n8n instance.

        Args:
            active: Filter by active status (None = all).
            tags: Filter by tag names.

        Returns:
            List of workflow dictionaries.
        """
        response = await self.client.get("/api/v1/workflows")
        response.raise_for_status()
        workflows: list[dict[str, Any]] = response.json().get("data", [])

        # Apply client-side filtering for active/inactive
        if active is not None:
            workflows = [w for w in workflows if w.get("active") == active]

        # Apply tag filtering
        if tags:
            workflows = [
                w for w in workflows
                if any(t.get("name") in tags for t in w.get("tags", []))
            ]

        return workflows
