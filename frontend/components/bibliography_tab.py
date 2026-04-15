"""Bibliography tab UI for the Gradio frontend."""

from __future__ import annotations

import gradio as gr

from frontend.backend_client import BackendClient, BackendClientError
from frontend.formatters import format_bibliography_markdown, split_identifiers
from frontend.i18n import Language, t


def build_bibliography_tab(lang_selector: gr.Radio, backend_client: BackendClient, default_language: Language) -> None:
    """Build the bibliography tab and wire its event handlers."""

    header = gr.Markdown(f"## {t(default_language, 'bibliography_title')}")
    query = gr.Textbox(
        label=t(default_language, "bibliography_query_label"),
        placeholder=t(default_language, "bibliography_query_placeholder"),
        lines=3,
    )
    identifiers = gr.Textbox(
        label=t(default_language, "bibliography_ids_label"),
        placeholder=t(default_language, "bibliography_ids_placeholder"),
        lines=6,
    )
    generate_button = gr.Button(t(default_language, "bibliography_button"), variant="primary")
    apa_output = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "bibliography_apa_label"))
    mla_output = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "bibliography_mla_label"))
    gost_output = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "bibliography_gost_label"))
    error_box = gr.Markdown("", label=t(default_language, "bibliography_error_label"), visible=False)

    def run_bibliography(language: Language, query_value: str, ids_value: str):
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
                t(language, "empty_state"),
                gr.update(value=t(language, "input_required"), visible=True),
            )
        try:
            data = backend_client.bibliography(payload)
        except BackendClientError as exc:
            return (
                t(language, "empty_state"),
                t(language, "empty_state"),
                t(language, "empty_state"),
                gr.update(value=str(exc), visible=True),
            )
        return (
            format_bibliography_markdown(data.get("apa7", []), language),
            format_bibliography_markdown(data.get("mla9", []), language),
            format_bibliography_markdown(data.get("gost", []), language),
            gr.update(value="", visible=False),
        )

    def update_ui(language: Language):
        return (
            gr.update(value=f"## {t(language, 'bibliography_title')}"),
            gr.update(label=t(language, "bibliography_query_label"), placeholder=t(language, "bibliography_query_placeholder")),
            gr.update(label=t(language, "bibliography_ids_label"), placeholder=t(language, "bibliography_ids_placeholder")),
            gr.update(value=t(language, "bibliography_button")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value="", visible=False),
        )

    generate_button.click(
        fn=run_bibliography,
        inputs=[lang_selector, query, identifiers],
        outputs=[apa_output, mla_output, gost_output, error_box],
        queue=False,
    )
    lang_selector.change(
        fn=update_ui,
        inputs=[lang_selector],
        outputs=[header, query, identifiers, generate_button, apa_output, mla_output, gost_output, error_box],
        queue=False,
    )
