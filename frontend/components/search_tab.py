"""Search tab UI for the Gradio frontend."""

from __future__ import annotations

import math
from typing import Any

import gradio as gr

from frontend.backend_client import BackendClient, BackendClientError
from frontend.formatters import format_papers_markdown, format_source_stats_markdown
from frontend.i18n import Language, t

_ALLOWED_SOURCES = {"semantic_scholar", "openalex", "crossref", "arxiv"}


def _coerce_optional_int(value: object) -> int | None:
    """Normalize optional numeric filters coming from Gradio inputs."""

    if value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            numeric = float(stripped)
        except ValueError:
            return None
        if not math.isfinite(numeric):
            return None
        return int(numeric)
    return None


def build_search_tab(lang_selector: gr.Radio, backend_client: BackendClient, default_language: Language) -> None:
    """Build the search tab and wire its event handlers."""

    header = gr.Markdown(f"## {t(default_language, 'search_title')}")
    with gr.Row():
        query = gr.Textbox(
            label=t(default_language, "search_query_label"),
            placeholder=t(default_language, "search_query_placeholder"),
            lines=3,
            scale=3,
        )
        with gr.Column(scale=2):
            limit = gr.Slider(1, 10, value=10, step=1, label=t(default_language, "limit_label"))
            year_from = gr.Number(label=t(default_language, "year_from_label"), precision=0, value=None)
            year_to = gr.Number(label=t(default_language, "year_to_label"), precision=0, value=None)
            source = gr.Dropdown(
                choices=[
                    (t(default_language, "source_any"), ""),
                    ("semantic_scholar", "semantic_scholar"),
                    ("openalex", "openalex"),
                    ("crossref", "crossref"),
                    ("arxiv", "arxiv"),
                ],
                value="",
                label=t(default_language, "source_label"),
            )
    search_button = gr.Button(t(default_language, "search_button"), variant="primary")
    results = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "search_results_label"))
    source_stats = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "search_stats_label"))
    error_box = gr.Markdown("", label=t(default_language, "search_error_label"), visible=False)

    def run_search(
        language: Language,
        query_value: str,
        limit_value: float,
        year_from_value: float | None,
        year_to_value: float | None,
        source_value: str,
    ) -> tuple[str, str, gr.Markdown]:
        if not query_value.strip():
            return (
                t(language, "no_results"),
                t(language, "empty_state"),
                gr.update(value=t(language, "input_required"), visible=True),
            )
        payload: dict[str, Any] = {
            "query": query_value,
            "language": language,
            "limit": int(limit_value),
        }
        year_from_clean = _coerce_optional_int(year_from_value)
        year_to_clean = _coerce_optional_int(year_to_value)
        if year_from_clean is not None:
            payload["year_from"] = year_from_clean
        if year_to_clean is not None:
            payload["year_to"] = year_to_clean
        if source_value in _ALLOWED_SOURCES:
            payload["source"] = source_value
        try:
            data = backend_client.search(payload)
        except BackendClientError as exc:
            return (
                t(language, "empty_state"),
                t(language, "empty_state"),
                gr.update(value=str(exc), visible=True),
            )
        return (
            format_papers_markdown(data.get("papers", []), language),
            format_source_stats_markdown(data.get("source_stats"), language),
            gr.update(value="", visible=False),
        )

    def update_ui(language: Language):
        return (
            gr.update(value=f"## {t(language, 'search_title')}"),
            gr.update(label=t(language, "search_query_label"), placeholder=t(language, "search_query_placeholder")),
            gr.update(label=t(language, "limit_label")),
            gr.update(label=t(language, "year_from_label"), value=None),
            gr.update(label=t(language, "year_to_label"), value=None),
            gr.update(
                label=t(language, "source_label"),
                choices=[
                    (t(language, "source_any"), ""),
                    ("semantic_scholar", "semantic_scholar"),
                    ("openalex", "openalex"),
                    ("crossref", "crossref"),
                    ("arxiv", "arxiv"),
                ],
            ),
            gr.update(value=t(language, "search_button")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value="", visible=False),
        )

    search_button.click(
        fn=run_search,
        inputs=[lang_selector, query, limit, year_from, year_to, source],
        outputs=[results, source_stats, error_box],
        queue=False,
    )
    lang_selector.change(
        fn=update_ui,
        inputs=[lang_selector],
        outputs=[header, query, limit, year_from, year_to, source, search_button, results, source_stats, error_box],
        queue=False,
    )
