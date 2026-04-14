"""Language detection and response helpers."""

from __future__ import annotations

from typing import Literal
import re


SupportedLanguage = Literal["ru", "en"]

_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


def detect_language(text: str) -> SupportedLanguage:
    """Detect whether the incoming text is predominantly Russian or English."""

    if _CYRILLIC_RE.search(text):
        return "ru"
    return "en"


def resolve_language(text: str, explicit_language: SupportedLanguage | None = None) -> SupportedLanguage:
    """Resolve the response language with an optional explicit override."""

    if explicit_language in {"ru", "en"}:
        return explicit_language
    return detect_language(text)


def language_label(language: SupportedLanguage) -> str:
    """Return a human-readable language label."""

    return "Russian" if language == "ru" else "English"
