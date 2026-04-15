"""Analytics tab UI for the Gradio frontend."""

from __future__ import annotations

import gradio as gr

from frontend.backend_client import BackendClient, BackendClientError
from frontend.formatters import format_analytics_markdown, format_papers_markdown, split_identifiers
from frontend.i18n import Language, t


def build_analytics_tab(lang_selector: gr.Radio, backend_client: BackendClient, default_language: Language) -> None:
    """Build the analytics tab and wire its event handlers."""

    header = gr.Markdown(f"## {t(default_language, 'analytics_title')}")
    query = gr.Textbox(
        label=t(default_language, "analytics_query_label"),
        placeholder=t(default_language, "analytics_query_placeholder"),
        lines=3,
    )
    identifiers = gr.Textbox(
        label=t(default_language, "analytics_ids_label"),
        placeholder=t(default_language, "analytics_ids_placeholder"),
        lines=6,
    )
    analytics_button = gr.Button(t(default_language, "analytics_button"), variant="primary")
    analytics_output = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "analytics_output_label"))
    papers_output = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "analytics_papers_label"))
    error_box = gr.Markdown("", label=t(default_language, "analytics_error_label"), visible=False)

    def run_analytics(language: Language, query_value: str, ids_value: str):
        dois, paper_ids = split_identifiers(ids_value)
        payload = {
            "query": query_value or None,
            "language": language,
            "dois": dois or None,
            "paper_ids": paper_ids or None,
            "limit": 10,
        }
        if not payload["query"] and not payload["dois"] and not payload["paper_ids"]:
            return (
                t(language, "empty_state"),
                t(language, "empty_state"),
                gr.update(value=t(language, "input_required"), visible=True),
            )
        try:
            data = backend_client.analytics(payload)
        except BackendClientError as exc:
            return (
                t(language, "empty_state"),
                t(language, "empty_state"),
                gr.update(value=str(exc), visible=True),
            )
        return (
            format_analytics_markdown(
                data.get("source_distribution", {}),
                data.get("year_distribution", {}),
                data.get("citation_stats", {}),
                language,
            ),
            format_papers_markdown(data.get("papers", []), language),
            gr.update(value="", visible=False),
        )

    def update_ui(language: Language):
        return (
            gr.update(value=f"## {t(language, 'analytics_title')}"),
            gr.update(label=t(language, "analytics_query_label"), placeholder=t(language, "analytics_query_placeholder")),
            gr.update(label=t(language, "analytics_ids_label"), placeholder=t(language, "analytics_ids_placeholder")),
            gr.update(value=t(language, "analytics_button")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value="", visible=False),
        )

    analytics_button.click(
        fn=run_analytics,
        inputs=[lang_selector, query, identifiers],
        outputs=[analytics_output, papers_output, error_box],
        queue=False,
    )
    lang_selector.change(
        fn=update_ui,
        inputs=[lang_selector],
        outputs=[header, query, identifiers, analytics_button, analytics_output, papers_output, error_box],
        queue=False,
    )
