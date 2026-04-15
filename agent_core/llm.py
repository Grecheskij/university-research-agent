"""LLM helpers for creating LangChain chat models when credentials are available."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
import logging

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

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


@dataclass(slots=True)
class _SimpleChatResult:
    """Small content wrapper compatible with extract_text()."""

    content: str


class FallbackChatModel:
    """Try multiple chat providers in order until one succeeds."""

    def __init__(self, providers: Sequence[tuple[str, Any]]) -> None:
        self.providers = list(providers)

    async def ainvoke(self, messages: Sequence[Any]) -> Any:
        """Invoke providers in order, falling back on external provider failures."""

        last_error: Exception | None = None
        for name, provider in self.providers:
            try:
                return await provider.ainvoke(messages)
            except Exception as exc:  # noqa: BLE001 - external provider fallback
                last_error = exc
                LOGGER.warning("LLM provider failed; trying fallback. provider=%s error=%s", name, type(exc).__name__)
        if last_error is not None:
            raise last_error
        raise RuntimeError("No LLM providers are configured.")

    async def aclose(self) -> None:
        """Close all providers that expose an async close hook."""

        for _, provider in self.providers:
            close = getattr(provider, "aclose", None)
            if callable(close):
                await close()


class OpenRouterChatModel:
    """Minimal OpenAI-compatible chat wrapper for OpenRouter."""

    def __init__(self, settings: CoreSettings) -> None:
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""

        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ainvoke(self, messages: Sequence[Any]) -> _SimpleChatResult:
        """Send chat messages to OpenRouter and return a content wrapper."""

        client = await self._get_client()
        base_payload: dict[str, Any] = {
            "messages": [self._serialize_message(message) for message in messages],
            "temperature": 0,
        }

        for model_name in self._candidate_models():
            payload = dict(base_payload)
            payload["model"] = model_name

            try:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(self.settings.retry_attempts),
                    wait=wait_exponential(
                        multiplier=self.settings.retry_min_seconds,
                        max=self.settings.retry_max_seconds,
                    ),
                    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
                    reraise=True,
                ):
                    with attempt:
                        response = await client.post("/chat/completions", json=payload)
                        response.raise_for_status()
                        body = response.json()
                        content = self._extract_content(body)
                        return _SimpleChatResult(content=content)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code in {402, 404} and model_name != "openrouter/free":
                    LOGGER.warning(
                        "OpenRouter model unavailable; trying free fallback. model=%s status=%s",
                        model_name,
                        status_code,
                    )
                    continue
                raise

        raise RuntimeError("OpenRouter request did not complete.")

    def _candidate_models(self) -> list[str]:
        """Return OpenRouter models to try in order."""

        candidates: list[str] = []
        if self.settings.openrouter_model:
            candidates.append(self.settings.openrouter_model)
        if "openrouter/free" not in candidates:
            candidates.append("openrouter/free")
        return candidates

    async def _get_client(self) -> httpx.AsyncClient:
        """Create the reusable OpenRouter client on demand."""

        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                "Content-Type": "application/json",
            }
            if self.settings.openrouter_site_url:
                headers["HTTP-Referer"] = self.settings.openrouter_site_url
            if self.settings.openrouter_app_title:
                headers["X-OpenRouter-Title"] = self.settings.openrouter_app_title

            self._client = httpx.AsyncClient(
                base_url=self.settings.openrouter_base_url,
                headers=headers,
                timeout=self.settings.request_timeout,
                trust_env=self.settings.http_trust_env,
            )
        return self._client

    def _serialize_message(self, message: Any) -> dict[str, Any]:
        """Normalize LangChain message objects into OpenAI-style dicts."""

        message_type = getattr(message, "type", "")
        role = {
            "system": "system",
            "human": "user",
            "ai": "assistant",
            "assistant": "assistant",
            "tool": "tool",
        }.get(message_type, "user")
        return {
            "role": role,
            "content": extract_text(message),
        }

    def _extract_content(self, payload: dict[str, Any]) -> str:
        """Extract assistant text from the OpenRouter chat response."""

        choices = payload.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content", "")
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


def create_chat_model(settings: CoreSettings | None = None) -> Any | None:
    """Create the preferred chat model, falling back from Gemini to OpenRouter to Groq."""

    runtime_settings = settings or get_settings()
    provider = runtime_settings.llm_provider

    if provider == "gemini":
        if runtime_settings.gemini_api_key and ChatGoogleGenerativeAI is not None:
            return ChatGoogleGenerativeAI(
                model=runtime_settings.gemini_model,
                google_api_key=runtime_settings.gemini_api_key,
                temperature=0,
            )
        LOGGER.warning("LLM_PROVIDER=gemini is set, but Gemini is not available.")
        return None

    if provider == "openrouter":
        if runtime_settings.openrouter_api_key:
            return OpenRouterChatModel(runtime_settings)
        LOGGER.warning("LLM_PROVIDER=openrouter is set, but OpenRouter is not available.")
        return None

    if provider == "groq":
        if runtime_settings.groq_api_key and ChatGroq is not None:
            return ChatGroq(
                model=runtime_settings.groq_model,
                api_key=runtime_settings.groq_api_key,
                temperature=0,
                max_retries=runtime_settings.retry_attempts,
                timeout=runtime_settings.request_timeout,
            )
        LOGGER.warning("LLM_PROVIDER=groq is set, but Groq is not available.")
        return None

    if provider == "auto":
        providers: list[tuple[str, Any]] = []
        if runtime_settings.gemini_api_key and ChatGoogleGenerativeAI is not None:
            providers.append(
                (
                    "gemini",
                    ChatGoogleGenerativeAI(
                        model=runtime_settings.gemini_model,
                        google_api_key=runtime_settings.gemini_api_key,
                        temperature=0,
                    ),
                )
            )
        if runtime_settings.openrouter_api_key:
            providers.append(("openrouter", OpenRouterChatModel(runtime_settings)))
        if runtime_settings.groq_api_key and ChatGroq is not None:
            providers.append(
                (
                    "groq",
                    ChatGroq(
                        model=runtime_settings.groq_model,
                        api_key=runtime_settings.groq_api_key,
                        temperature=0,
                        max_retries=runtime_settings.retry_attempts,
                        timeout=runtime_settings.request_timeout,
                    ),
                )
            )
        if providers:
            return FallbackChatModel(providers)

    if runtime_settings.gemini_api_key and ChatGoogleGenerativeAI is not None:
        return ChatGoogleGenerativeAI(
            model=runtime_settings.gemini_model,
            google_api_key=runtime_settings.gemini_api_key,
            temperature=0,
        )

    if runtime_settings.openrouter_api_key:
        return OpenRouterChatModel(runtime_settings)

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
