"""LLM helpers for creating LangChain chat models when credentials are available."""

from __future__ import annotations

from typing import Any
import logging

from agent_core.config import CoreSettings, get_settings

LOGGER = logging.getLogger(__name__)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - optional dependency
    ChatGoogleGenerativeAI = None

try:
    from langchain_groq import ChatGroq
except ImportError:  # pragma: no cover - optional dependency
    ChatGroq = None


def create_chat_model(settings: CoreSettings | None = None) -> Any | None:
    """Create the preferred chat model, falling back from Gemini to Groq."""

    runtime_settings = settings or get_settings()

    if runtime_settings.gemini_api_key and ChatGoogleGenerativeAI is not None:
        return ChatGoogleGenerativeAI(
            model=runtime_settings.gemini_model,
            google_api_key=runtime_settings.gemini_api_key,
            temperature=0,
        )

    if runtime_settings.groq_api_key and ChatGroq is not None:
        return ChatGroq(
            model=runtime_settings.groq_model,
            api_key=runtime_settings.groq_api_key,
            temperature=0,
            max_retries=runtime_settings.retry_attempts,
            timeout=runtime_settings.request_timeout,
        )

    LOGGER.warning(
        "No LLM provider is available; falling back to deterministic chain outputs."
    )
    return None


def extract_text(result: Any) -> str:
    """Normalize LangChain chat model output into plain text."""

    content = getattr(result, "content", result)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")).strip())
            else:
                text_parts.append(str(item).strip())
        return "\n".join(part for part in text_parts if part).strip()
    return str(content).strip()
