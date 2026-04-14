"""Shared HTTP primitives for research source tools."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any
import logging

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from agent_core.config import CoreSettings, get_settings

LOGGER = logging.getLogger(__name__)


class ResearchToolError(RuntimeError):
    """Raised when an upstream research data provider fails."""


class RetriableHTTPStatusError(ResearchToolError):
    """Raised for HTTP statuses that should be retried."""


class BaseResearchHTTPTool:
    """Base helper for source-specific research tools."""

    source_name: str = "source"

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._external_client = client
        self._client: httpx.AsyncClient | None = client

    async def close(self) -> None:
        """Close the internal HTTP client if the tool created it."""

        if self._client is not None and self._external_client is None:
            await self._client.aclose()
            self._client = None

    def _default_headers(self) -> dict[str, str]:
        """Build default headers without exposing secrets."""

        return {
            "Accept": "application/json",
            "User-Agent": self.settings.user_agent,
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a reusable async client."""

        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._default_headers(),
                timeout=self.settings.request_timeout,
            )
        return self._client

    async def _after_request(self) -> None:
        """Optional hook for provider-specific throttling."""

    async def _request_json(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Perform a JSON request with retry, logging, and error handling."""

        client = await self._get_client()
        merged_headers = dict(headers or {})
        start_time = perf_counter()
        request_completed = False

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.settings.retry_attempts),
                wait=wait_exponential(
                    multiplier=self.settings.retry_min_seconds,
                    max=self.settings.retry_max_seconds,
                ),
                retry=retry_if_exception_type(
                    (httpx.TimeoutException, httpx.NetworkError, RetriableHTTPStatusError)
                ),
                reraise=True,
            ):
                with attempt:
                    response = await client.get(path, params=params, headers=merged_headers or None)
                    request_completed = True
                    self._log_response(path=path, status=response.status_code, start_time=start_time)
                    if response.status_code >= 500 or response.status_code == 429:
                        raise RetriableHTTPStatusError(
                            f"{self.source_name} temporary failure: {response.status_code}"
                        )
                    if response.status_code >= 400:
                        raise ResearchToolError(
                            f"{self.source_name} request failed with status {response.status_code}"
                        )
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise ResearchToolError(
                            f"{self.source_name} returned invalid JSON"
                        ) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            self._log_exception(path=path, start_time=start_time, exc=exc)
            raise ResearchToolError(f"{self.source_name} request failed: {exc}") from exc
        except RetriableHTTPStatusError as exc:
            raise ResearchToolError(str(exc)) from exc
        finally:
            if request_completed:
                await self._after_request()

    async def _request_text(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        """Perform a text request with retry, logging, and error handling."""

        client = await self._get_client()
        merged_headers = dict(headers or {})
        start_time = perf_counter()
        request_completed = False

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.settings.retry_attempts),
                wait=wait_exponential(
                    multiplier=self.settings.retry_min_seconds,
                    max=self.settings.retry_max_seconds,
                ),
                retry=retry_if_exception_type(
                    (httpx.TimeoutException, httpx.NetworkError, RetriableHTTPStatusError)
                ),
                reraise=True,
            ):
                with attempt:
                    response = await client.get(path, params=params, headers=merged_headers or None)
                    request_completed = True
                    self._log_response(path=path, status=response.status_code, start_time=start_time)
                    if response.status_code >= 500 or response.status_code == 429:
                        raise RetriableHTTPStatusError(
                            f"{self.source_name} temporary failure: {response.status_code}"
                        )
                    if response.status_code >= 400:
                        raise ResearchToolError(
                            f"{self.source_name} request failed with status {response.status_code}"
                        )
                    return response.text
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            self._log_exception(path=path, start_time=start_time, exc=exc)
            raise ResearchToolError(f"{self.source_name} request failed: {exc}") from exc
        except RetriableHTTPStatusError as exc:
            raise ResearchToolError(str(exc)) from exc
        finally:
            if request_completed:
                await self._after_request()

    def _log_response(self, *, path: str, status: int, start_time: float) -> None:
        """Log metadata about a successful or failed response."""

        elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
        LOGGER.info(
            "research_api_request source=%s endpoint=%s status=%s duration_ms=%s",
            self.source_name,
            path,
            status,
            elapsed_ms,
        )

    def _log_exception(self, *, path: str, start_time: float, exc: Exception) -> None:
        """Log metadata about request exceptions."""

        elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
        LOGGER.warning(
            "research_api_request_failed source=%s endpoint=%s error=%s duration_ms=%s",
            self.source_name,
            path,
            exc.__class__.__name__,
            elapsed_ms,
        )
