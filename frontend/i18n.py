"""UI text catalog for the bilingual Gradio frontend."""

from __future__ import annotations

from typing import Literal
import os


Language = Literal["ru", "en"]


UI_TEXT: dict[Language, dict[str, str]] = {
    "ru": {
        "app_title": "University Research Agent",
        "app_intro": "ИИ-ассистент для поиска статей, обзора литературы, библиографии и аналитики.",
        "language_label": "Язык интерфейса",
        "backend_status": "Backend API: {url}",
        "tab_search": "Поиск / Search",
        "tab_review": "Обзор / Review",
        "tab_bibliography": "Библиография / Bibliography",
        "tab_analytics": "Аналитика / Analytics",
        "search_title": "Поиск статей",
        "search_query_label": "Поисковый запрос",
        "search_query_placeholder": "Например: retrieval-augmented generation in education",
        "limit_label": "Лимит результатов",
        "year_from_label": "Год от",
        "year_to_label": "Год до",
        "source_label": "Источник",
        "source_any": "Любой",
        "search_button": "Искать",
        "search_results_label": "Результаты поиска",
        "search_stats_label": "Статистика по источникам",
        "search_error_label": "Ошибка поиска",
        "review_title": "Обзор литературы",
        "review_query_label": "Тема обзора",
        "review_query_placeholder": "Опишите тему обзора литературы",
        "review_ids_label": "DOI или ID (по одному на строку)",
        "review_ids_placeholder": "10.1000/xyz123\nW1234567890",
        "review_button": "Сделать обзор",
        "review_output_label": "Обзор",
        "review_papers_label": "Статьи в обзоре",
        "review_error_label": "Ошибка обзора",
        "bibliography_title": "Формирование библиографии",
        "bibliography_query_label": "Тема или ключевые слова",
        "bibliography_query_placeholder": "Необязательно, если вы уже указываете DOI/ID",
        "bibliography_ids_label": "DOI или ID (по одному на строку)",
        "bibliography_ids_placeholder": "10.1000/xyz123\n10.1000/xyz456",
        "bibliography_button": "Сформировать библиографию",
        "bibliography_apa_label": "APA 7",
        "bibliography_mla_label": "MLA 9",
        "bibliography_gost_label": "ГОСТ 7.0.5",
        "bibliography_error_label": "Ошибка библиографии",
        "analytics_title": "Аналитика по корпусу статей",
        "analytics_query_label": "Тема или ключевые слова",
        "analytics_query_placeholder": "Например: academic writing assistants",
        "analytics_ids_label": "DOI или ID (по одному на строку)",
        "analytics_ids_placeholder": "Оставьте пустым, если анализ строится по запросу",
        "analytics_button": "Построить аналитику",
        "analytics_output_label": "Аналитика",
        "analytics_papers_label": "Статьи в выборке",
        "analytics_error_label": "Ошибка аналитики",
        "empty_state": "Пока нет данных. Запустите запрос, чтобы увидеть результат.",
        "request_failed": "Не удалось обратиться к backend API.",
        "input_required": "Заполните запрос или список идентификаторов.",
        "no_results": "Ничего не найдено.",
        "summary_sources": "Источники",
        "summary_citations": "Цитирования",
    },
    "en": {
        "app_title": "University Research Agent",
        "app_intro": "AI assistant for paper search, literature reviews, bibliography generation, and analytics.",
        "language_label": "Interface language",
        "backend_status": "Backend API: {url}",
        "tab_search": "Search / Поиск",
        "tab_review": "Review / Обзор",
        "tab_bibliography": "Bibliography / Библиография",
        "tab_analytics": "Analytics / Аналитика",
        "search_title": "Paper Search",
        "search_query_label": "Search query",
        "search_query_placeholder": "For example: retrieval-augmented generation in education",
        "limit_label": "Result limit",
        "year_from_label": "Year from",
        "year_to_label": "Year to",
        "source_label": "Source",
        "source_any": "Any",
        "search_button": "Search",
        "search_results_label": "Search results",
        "search_stats_label": "Source statistics",
        "search_error_label": "Search error",
        "review_title": "Literature Review",
        "review_query_label": "Review topic",
        "review_query_placeholder": "Describe the review topic",
        "review_ids_label": "DOIs or IDs (one per line)",
        "review_ids_placeholder": "10.1000/xyz123\nW1234567890",
        "review_button": "Generate review",
        "review_output_label": "Review output",
        "review_papers_label": "Papers used in review",
        "review_error_label": "Review error",
        "bibliography_title": "Bibliography Builder",
        "bibliography_query_label": "Topic or keywords",
        "bibliography_query_placeholder": "Optional if you already provide DOI/ID values",
        "bibliography_ids_label": "DOIs or IDs (one per line)",
        "bibliography_ids_placeholder": "10.1000/xyz123\n10.1000/xyz456",
        "bibliography_button": "Build bibliography",
        "bibliography_apa_label": "APA 7",
        "bibliography_mla_label": "MLA 9",
        "bibliography_gost_label": "GOST 7.0.5",
        "bibliography_error_label": "Bibliography error",
        "analytics_title": "Corpus Analytics",
        "analytics_query_label": "Topic or keywords",
        "analytics_query_placeholder": "For example: academic writing assistants",
        "analytics_ids_label": "DOIs or IDs (one per line)",
        "analytics_ids_placeholder": "Leave empty if analytics should use the query",
        "analytics_button": "Run analytics",
        "analytics_output_label": "Analytics output",
        "analytics_papers_label": "Papers in scope",
        "analytics_error_label": "Analytics error",
        "empty_state": "No data yet. Run a request to see results.",
        "request_failed": "Could not reach the backend API.",
        "input_required": "Please provide a query or a list of identifiers.",
        "no_results": "No results were found.",
        "summary_sources": "Sources",
        "summary_citations": "Citations",
    },
}


def get_default_language() -> Language:
    """Return the default UI language from environment configuration."""

    value = os.getenv("FRONTEND_LANG_DEFAULT", "ru").strip().lower()
    return "en" if value == "en" else "ru"


def t(language: Language, key: str) -> str:
    """Return a translated UI string for the requested key."""

    return UI_TEXT[language][key]
