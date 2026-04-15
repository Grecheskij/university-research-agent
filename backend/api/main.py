"""FastAPI application factory for the research backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env", override=True)

from backend.api.config import BackendSettings, get_backend_settings
from backend.api.errors import AppError
from backend.api.models.response_models import ErrorResponse, HealthResponse
from backend.api.routes.analytics import router as analytics_router
from backend.api.routes.bibliography import router as bibliography_router
from backend.api.routes.review import router as review_router
from backend.api.routes.search import router as search_router
from backend.api.services import ResearchBackendService

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared backend resources during application lifetime."""

    yield
    service = getattr(app.state, "research_service", None)
    if service is not None:
        await service.close()


def create_app(
    *,
    settings: BackendSettings | None = None,
    research_service: ResearchBackendService | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""

    runtime_settings = settings or get_backend_settings()
    app = FastAPI(
        title=runtime_settings.app_name,
        description=runtime_settings.app_description,
        version=runtime_settings.app_version,
        lifespan=lifespan,
    )
    app.state.backend_settings = runtime_settings
    app.state.research_service = research_service or ResearchBackendService()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    @app.middleware("http")
    async def enforce_request_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > runtime_settings.max_request_bytes:
                    payload = ErrorResponse(
                        code="payload_too_large",
                        message="Request body is too large.",
                        details={"max_request_bytes": runtime_settings.max_request_bytes},
                    )
                    return JSONResponse(status_code=413, content=payload.model_dump())
            except ValueError:
                LOGGER.warning("Invalid content-length header received.")
        return await call_next(request)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        payload = ErrorResponse(code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(
            code="validation_error",
            message="Request validation failed.",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception("Unhandled backend exception: %s", exc.__class__.__name__)
        payload = ErrorResponse(
            code="internal_error",
            message="An unexpected server error occurred.",
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def healthcheck() -> HealthResponse:
        """Return the service health status."""

        return HealthResponse(status="ok")

    app.include_router(search_router)
    app.include_router(review_router)
    app.include_router(bibliography_router)
    app.include_router(analytics_router)
    return app


app = create_app()
