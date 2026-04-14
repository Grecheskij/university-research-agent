"""HTTP client for communicating with the FastAPI backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os

import httpx


class BackendClientError(RuntimeError):
    """Raised when the frontend cannot complete a backend request."""


@dataclass(slots=True)
class BackendClient:
    """Thin wrapper over httpx for frontend-to-backend communication."""

    base_url: str
    timeout: float = 30.0
    api_key: str | None = None

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the search API endpoint."""

        return self._post("/api/search/", payload)

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the review API endpoint."""

        return self._post("/api/review/", payload)

    def bibliography(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the bibliography API endpoint."""

        return self._post("/api/bibliography/", payload)

    def analytics(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the analytics API endpoint."""

        return self._post("/api/analytics/", payload)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform a POST request and normalize backend errors."""

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout, headers=headers) as client:
                response = client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise BackendClientError("The backend request timed out.") from exc
        except httpx.HTTPError as exc:
            raise BackendClientError(f"Could not reach backend: {exc}") from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError as exc:
                raise BackendClientError(
                    f"Backend returned status {response.status_code}."
                ) from exc
            message = body.get("message") or f"Backend returned status {response.status_code}."
            code = body.get("code")
            if code:
                raise BackendClientError(f"{message} ({code})")
            raise BackendClientError(message)

        try:
            return response.json()
        except ValueError as exc:
            raise BackendClientError("Backend returned invalid JSON.") from exc


def create_backend_client() -> BackendClient:
    """Create a backend client from environment variables."""

    return BackendClient(
        base_url=os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
        timeout=float(os.getenv("FRONTEND_HTTP_TIMEOUT", "30")),
        api_key=os.getenv("BACKEND_API_KEY") or os.getenv("API_KEY"),
    )
