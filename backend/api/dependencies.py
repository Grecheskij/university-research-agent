"""FastAPI dependencies for shared backend services and guards."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, Request

from backend.api.config import BackendSettings, get_backend_settings
from backend.api.errors import AppError
from backend.api.services import ResearchBackendService


def get_backend_service(request: Request) -> ResearchBackendService:
    """Return the shared backend service from application state."""

    return request.app.state.research_service


def get_backend_runtime_settings(request: Request) -> BackendSettings:
    """Return backend runtime settings from application state."""

    return request.app.state.backend_settings


async def require_optional_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Validate the API key only when one is configured."""

    settings = get_backend_runtime_settings(request)
    if settings.api_key is None:
        return
    if x_api_key != settings.api_key:
        raise AppError(
            code="unauthorized",
            message="A valid X-API-Key header is required for this endpoint.",
            status_code=401,
        )
