"""Prompt helpers for the literature review chain."""

from __future__ import annotations

from agent_core.language import SupportedLanguage
from agent_core.prompts.system_prompt import build_chat_prompt, build_system_prompt


def get_review_prompt(language: SupportedLanguage):
    """Return the review chain prompt template."""

    system_prompt = build_system_prompt(
        language,
        task_hint=(
            "Подготовь академический обзор литературы с тематическими группами, "
            "сравнением работ и явными исследовательскими пробелами."
        ),
    )
    human_prompt = """
Пользовательский запрос:
{user_query}

Основные статьи:
{papers_context}

RAG-контекст из локальной базы:
{rag_context}

Сформируй 1 сжатый академический обзор, который поможет исследователю быстро понять поле.
"""
    return build_chat_prompt(system_prompt, human_prompt)
