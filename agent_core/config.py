"""Configuration helpers for the research agent core."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=True)


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


@dataclass(slots=True, frozen=True)
class CoreSettings:
    """Runtime settings loaded from environment variables."""

    semantic_scholar_base_url: str
    openalex_base_url: str
    crossref_base_url: str
    arxiv_base_url: str
    unpaywall_base_url: str
    semantic_scholar_api_key: str | None
    unpaywall_email: str | None
    contact_email: str | None
    gemini_api_key: str | None
    groq_api_key: str | None
    gemini_model: str
    groq_model: str
    chroma_path: Path
    chroma_collection_name: str
    sentence_transformer_model: str
    request_timeout: float
    max_results: int
    retry_attempts: int
    retry_min_seconds: float
    retry_max_seconds: float
    llm_provider: str = "auto"
    openrouter_api_key: str | None = None
    openrouter_model: str | None = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str | None = None
    openrouter_app_title: str | None = "University Research Agent"
    http_trust_env: bool = False
    source_timeout: float = 12.0

    @property
    def user_agent(self) -> str:
        """Return a contact-friendly user agent string."""

        if self.contact_email:
            return f"university-research-agent/1.0 ({self.contact_email})"
        return "university-research-agent/1.0"

    @classmethod
    def from_env(cls) -> "CoreSettings":
        """Build settings from environment variables."""

        chroma_path = Path(os.getenv("CHROMA_PATH", "./data/chroma_db")).expanduser()
        return cls(
            semantic_scholar_base_url=os.getenv(
                "SEMANTIC_SCHOLAR_BASE_URL",
                "https://api.semanticscholar.org/graph/v1",
            ),
            openalex_base_url=os.getenv("OPENALEX_BASE_URL", "https://api.openalex.org"),
            crossref_base_url=os.getenv("CROSSREF_BASE_URL", "https://api.crossref.org"),
            arxiv_base_url=os.getenv("ARXIV_BASE_URL", "http://export.arxiv.org/api"),
            unpaywall_base_url=os.getenv("UNPAYWALL_BASE_URL", "https://api.unpaywall.org/v2"),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_KEY"),
            unpaywall_email=os.getenv("UNPAYWALL_EMAIL"),
            contact_email=os.getenv("RESEARCH_AGENT_CONTACT_EMAIL") or os.getenv("UNPAYWALL_EMAIL"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openrouter/free").strip() or "openrouter/free",
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openrouter_site_url=os.getenv("OPENROUTER_SITE_URL") or None,
            openrouter_app_title=os.getenv("OPENROUTER_APP_TITLE", "University Research Agent"),
            chroma_path=chroma_path,
            chroma_collection_name=os.getenv("CHROMA_COLLECTION_NAME", "research_papers"),
            sentence_transformer_model=os.getenv(
                "SENTENCE_TRANSFORMER_MODEL",
                "all-MiniLM-L6-v2",
            ),
            http_trust_env=_env_bool("HTTP_TRUST_ENV", False),
            request_timeout=_env_float("HTTP_TIMEOUT_SECONDS", 30.0),
            source_timeout=_env_float("RESEARCH_SOURCE_TIMEOUT_SECONDS", 12.0),
            max_results=_env_int("RESEARCH_MAX_RESULTS", 10),
            retry_attempts=_env_int("RESEARCH_RETRY_ATTEMPTS", 3),
            retry_min_seconds=_env_float("RESEARCH_RETRY_MIN_SECONDS", 1.0),
            retry_max_seconds=_env_float("RESEARCH_RETRY_MAX_SECONDS", 8.0),
            llm_provider=os.getenv("LLM_PROVIDER", "auto").strip().lower(),
        )


def get_settings() -> CoreSettings:
    """Return a fresh settings object."""

    return CoreSettings.from_env()
