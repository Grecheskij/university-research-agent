"""System prompt builders for the research agent."""

from __future__ import annotations

from agent_core.language import SupportedLanguage

try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:  # pragma: no cover - optional dependency
    ChatPromptTemplate = None


BASE_SYSTEM_PROMPT = """
Ты — исследовательский ИИ-ассистент для университета.
Соблюдай академический стиль, не выдумывай источники и опирайся только на переданные статьи и контекст.
Если данных недостаточно, прямо отмечай ограничения.
"""

LANGUAGE_INSTRUCTIONS: dict[SupportedLanguage, str] = {
    "ru": "Финальный ответ должен быть полностью на русском языке.",
    "en": "The final answer must be entirely in English.",
}


def build_system_prompt(language: SupportedLanguage, *, task_hint: str) -> str:
    """Build a system prompt for a specific task and language."""

    return "\n".join(
        [
            BASE_SYSTEM_PROMPT.strip(),
            LANGUAGE_INSTRUCTIONS[language],
            f"Текущая задача: {task_hint}",
        ]
    )


def build_chat_prompt(system_prompt: str, human_prompt: str):
    """Build a LangChain chat prompt when the dependency is available."""

    if ChatPromptTemplate is None:
        return None
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", human_prompt),
        ]
    )
