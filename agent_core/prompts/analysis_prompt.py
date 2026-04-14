"""Prompt helpers for summary and bibliography chains."""

from __future__ import annotations

from agent_core.language import SupportedLanguage
from agent_core.prompts.system_prompt import build_chat_prompt, build_system_prompt


def get_summary_prompt(language: SupportedLanguage):
    """Return the summary chain prompt template."""

    system_prompt = build_system_prompt(
        language,
        task_hint=(
            "Сделай краткую исследовательскую выжимку: общая идея, ключевые результаты "
            "и направления будущей работы."
        ),
    )
    human_prompt = """
Пользовательский запрос:
{user_query}

Статьи:
{papers_context}

RAG-контекст:
{rag_context}

Подготовь краткий, но содержательный исследовательский summary.
"""
    return build_chat_prompt(system_prompt, human_prompt)


def get_bibliography_prompt(language: SupportedLanguage):
    """Return the bibliography formatting prompt template."""

    system_prompt = build_system_prompt(
        language,
        task_hint=(
            "Подготовь библиографический список и проверь, что каждая запись соответствует "
            "требуемому стилю оформления."
        ),
    )
    human_prompt = """
Статьи:
{papers_context}

Нужно представить библиографию в стилях APA 7, MLA 9 и ГОСТ 7.0.5.
"""
    return build_chat_prompt(system_prompt, human_prompt)
