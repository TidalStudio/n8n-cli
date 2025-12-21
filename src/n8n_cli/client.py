"""HTTP client for interacting with the n8n API."""

from types import TracebackType
from typing import Any, Self

import httpx

from n8n_cli.exceptions import (
    ApiError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    TimeoutError,
    ValidationError,
)


def _extract_error_message(response: httpx.Response) -> str:
    """Extract error message from API response.

    Args:
        response: The HTTP response.

    Returns:
        Error message from JSON body or default message.
    """
    try:
        data = response.json()
        # n8n API returns error messages in "message" field
        if isinstance(data, dict) and "message" in data:
            return str(data["message"])
    except Exception:
        pass
    return f"HTTP {response.status_code}"


def _translate_http_error(
    error: httpx.HTTPStatusError,
    resource_type: str = "Resource",
    resource_id: str | None = None,
) -> None:
    """Translate httpx HTTP errors to custom exceptions.

    Args:
        error: The httpx HTTP status error.
        resource_type: Type of resource for 404 messages (e.g., "Workflow").
        resource_id: ID of resource for 404 messages.

    Raises:
        AuthenticationError: For 401 errors.
        NotFoundError: For 404 errors.
        ValidationError: For 400 errors.
        ApiError: For other HTTP errors.
    """
    status_code = error.response.status_code
    message = _extract_error_message(error.response)

    if status_code == 401:
        raise AuthenticationError(
            "Invalid or expired API key. Run 'n8n-cli configure' to update credentials."
        ) from error

    if status_code == 404:
        if resource_id:
            raise NotFoundError(f"{resource_type} not found: {resource_id}") from error
        raise NotFoundError(f"{resource_type} not found") from error

    if status_code == 400:
        raise ValidationError(message) from error

    raise ApiError(f"API error ({status_code}): {message}", status_code) from error


def _translate_connection_error(error: Exception, base_url: str) -> None:
    """Translate httpx connection errors to custom exceptions.

    Args:
        error: The httpx connection error.
        base_url: The base URL being connected to.

    Raises:
        ConnectionError: For connection failures.
        TimeoutError: For timeout errors.
    """
    if isinstance(error, httpx.TimeoutException):
        raise TimeoutError(
            "Request timed out. Try increasing timeout or check if n8n is responsive."
        ) from error

    if isinstance(error, httpx.ConnectError):
        raise ConnectionError(
            f"Cannot connect to n8n at {base_url}. "
            "Check the URL and ensure n8n is running."
        ) from error

    # Generic connection error
    raise ConnectionError(
        f"Connection error: {error}. Check your network and n8n URL."
    ) from error


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
            NotFoundError: If workflow not found (404).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.get(f"/api/v1/workflows/{workflow_id}")
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflow", workflow_id)
            raise  # unreachable, but keeps type checker happy
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

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

        Raises:
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
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
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflows")
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def create_workflow(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow.

        Args:
            workflow_data: Workflow definition (name, nodes, connections, etc.)

        Returns:
            Created workflow with assigned ID.

        Raises:
            ValidationError: If workflow data is invalid (400).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        # Strip fields that the n8n API doesn't accept on create
        # These fields are often present in exported workflow JSON files
        disallowed_fields = {
            "id",
            "staticData",
            "tags",
            "triggerCount",
            "pinData",
            "versionId",
            "createdAt",
            "updatedAt",
            "homeProject",
            "sharedWithProjects",
        }
        clean_data = {k: v for k, v in workflow_data.items() if k not in disallowed_fields}

        try:
            response = await self.client.post("/api/v1/workflows", json=clean_data)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflow")
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def activate_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Activate a workflow by ID.

        Args:
            workflow_id: The workflow ID to activate.

        Returns:
            Updated workflow with active=True.

        Raises:
            NotFoundError: If workflow not found (404).
            ValidationError: If workflow cannot be activated (400).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.patch(
                f"/api/v1/workflows/{workflow_id}",
                json={"active": True},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflow", workflow_id)
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def deactivate_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Deactivate a workflow by ID.

        Args:
            workflow_id: The workflow ID to deactivate.

        Returns:
            Updated workflow with active=False.

        Raises:
            NotFoundError: If workflow not found (404).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.patch(
                f"/api/v1/workflows/{workflow_id}",
                json={"active": False},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflow", workflow_id)
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def update_workflow(
        self, workflow_id: str, workflow_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing workflow.

        Args:
            workflow_id: The workflow ID to update.
            workflow_data: Updated workflow definition.

        Returns:
            Updated workflow.

        Raises:
            NotFoundError: If workflow not found (404).
            ValidationError: If workflow data is invalid (400).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.put(
                f"/api/v1/workflows/{workflow_id}",
                json=workflow_data,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflow", workflow_id)
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def delete_workflow(self, workflow_id: str) -> None:
        """Delete a workflow by ID.

        Args:
            workflow_id: The workflow ID to delete.

        Raises:
            NotFoundError: If workflow not found (404).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.delete(f"/api/v1/workflows/{workflow_id}")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflow", workflow_id)
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def execute_workflow(
        self,
        workflow_id: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a workflow by ID.

        Args:
            workflow_id: The workflow ID to execute.
            data: Optional input data to pass to the workflow.

        Returns:
            Execution info with executionId field.

        Raises:
            NotFoundError: If workflow not found (404).
            ValidationError: If workflow is inactive or input invalid (400).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            body: dict[str, Any] = {}
            if data is not None:
                body["inputData"] = data
            response = await self.client.post(
                f"/api/v1/workflows/{workflow_id}/execute",
                json=body,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Workflow", workflow_id)
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        """Get execution status and data.

        Args:
            execution_id: The execution ID to fetch.

        Returns:
            Execution details including status and output data.

        Raises:
            NotFoundError: If execution not found (404).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.get(f"/api/v1/executions/{execution_id}")
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Execution", execution_id)
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def get_executions(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Fetch executions with optional filters.

        Args:
            workflow_id: Filter by workflow ID.
            status: Filter by status (success, error, running, waiting, canceled).
            limit: Max number of results (default 20, max 250).

        Returns:
            List of execution dictionaries.

        Raises:
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            params: dict[str, Any] = {"limit": min(limit, 250), "includeData": "false"}
            if workflow_id:
                params["workflowId"] = workflow_id
            if status:
                params["status"] = status

            response = await self.client.get("/api/v1/executions", params=params)
            response.raise_for_status()
            executions: list[dict[str, Any]] = response.json().get("data", [])
            return executions
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Executions")
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def get_credentials(
        self,
        credential_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch credentials from n8n instance.

        Args:
            credential_type: Filter by credential type (e.g., "httpBasicAuth").

        Returns:
            List of credential dictionaries.

        Raises:
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.get("/api/v1/credentials")
            response.raise_for_status()
            credentials: list[dict[str, Any]] = response.json().get("data", [])

            # Apply client-side filtering by type
            if credential_type:
                credentials = [
                    c for c in credentials if c.get("type") == credential_type
                ]

            return credentials
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Credentials")
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def get_credential(self, credential_id: str) -> dict[str, Any]:
        """Fetch a single credential by ID.

        Args:
            credential_id: The credential ID.

        Returns:
            Credential details including data fields.

        Raises:
            NotFoundError: If credential not found (404).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            response = await self.client.get(f"/api/v1/credentials/{credential_id}")
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Credential", credential_id)
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise

    async def create_credential(
        self,
        name: str,
        credential_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new credential.

        Args:
            name: Display name for the credential.
            credential_type: The credential type (e.g., "httpBasicAuth").
            data: The credential data (secrets, tokens, etc.).

        Returns:
            Created credential with assigned ID.

        Raises:
            ValidationError: If credential data is invalid (400).
            AuthenticationError: If API key is invalid (401).
            ConnectionError: If cannot connect to n8n.
            ApiError: For other API errors.
        """
        try:
            payload = {
                "name": name,
                "type": credential_type,
                "data": data,
            }
            response = await self.client.post("/api/v1/credentials", json=payload)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            _translate_http_error(e, "Credential")
            raise
        except httpx.HTTPError as e:
            _translate_connection_error(e, self.base_url)
            raise
