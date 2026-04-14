"""Configuration helpers for the FastAPI backend."""

from __future__ import annotations

from dataclasses import dataclass
import os


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _split_origins(raw_value: str) -> list[str]:
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


@dataclass(slots=True, frozen=True)
class BackendSettings:
    """Runtime settings for the FastAPI application."""

    app_name: str
    app_description: str
    app_version: str
    frontend_origins: list[str]
    api_key: str | None
    max_request_bytes: int

    @classmethod
    def from_env(cls) -> "BackendSettings":
        """Load backend settings from environment variables."""

        default_origins = [
            "http://localhost:7860",
            "http://localhost:8000",
            "http://127.0.0.1:7860",
            "http://127.0.0.1:8000",
        ]
        configured_origins = _split_origins(os.getenv("FRONTEND_ORIGINS", ""))
        hf_space_url = os.getenv("HF_SPACE_URL")
        if hf_space_url:
            configured_origins.append(hf_space_url.strip())

        origins = configured_origins or default_origins
        return cls(
            app_name=os.getenv("BACKEND_APP_NAME", "University Research Agent API"),
            app_description=os.getenv(
                "BACKEND_APP_DESCRIPTION",
                "FastAPI service for research search, review, bibliography, and analytics.",
            ),
            app_version=os.getenv("BACKEND_APP_VERSION", "0.2.0"),
            frontend_origins=origins,
            api_key=os.getenv("BACKEND_API_KEY"),
            max_request_bytes=_env_int("BACKEND_MAX_REQUEST_BYTES", 1_048_576),
        )


def get_backend_settings() -> BackendSettings:
    """Return a fresh backend settings instance."""

    return BackendSettings.from_env()
