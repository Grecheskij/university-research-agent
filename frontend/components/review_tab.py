"""Review tab UI for the Gradio frontend."""

from __future__ import annotations

import gradio as gr

from frontend.backend_client import BackendClient, BackendClientError
from frontend.formatters import format_papers_markdown, split_identifiers
from frontend.i18n import Language, t


def build_review_tab(lang_selector: gr.Radio, backend_client: BackendClient, default_language: Language) -> None:
    """Build the review tab and wire its event handlers."""

    header = gr.Markdown(f"## {t(default_language, 'review_title')}")
    query = gr.Textbox(
        label=t(default_language, "review_query_label"),
        placeholder=t(default_language, "review_query_placeholder"),
        lines=4,
    )
    identifiers = gr.Textbox(
        label=t(default_language, "review_ids_label"),
        placeholder=t(default_language, "review_ids_placeholder"),
        lines=5,
    )
    review_button = gr.Button(t(default_language, "review_button"), variant="primary")
    review_output = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "review_output_label"))
    papers_output = gr.Markdown(t(default_language, "empty_state"), label=t(default_language, "review_papers_label"))
    error_box = gr.Markdown("", label=t(default_language, "review_error_label"), visible=False)

    def run_review(language: Language, query_value: str, ids_value: str) -> tuple[str, str, gr.Markdown]:
        dois, paper_ids = split_identifiers(ids_value)
        if not query_value.strip() and not dois and not paper_ids:
            return (
                t(language, "empty_state"),
                t(language, "empty_state"),
                gr.update(value=t(language, "input_required"), visible=True),
            )
        payload = {
            "query": query_value or "literature review",
            "language": language,
            "dois": dois or None,
            "paper_ids": paper_ids or None,
            "limit": 10,
        }
        try:
            data = backend_client.review(payload)
        except BackendClientError as exc:
            return (
                t(language, "empty_state"),
                t(language, "empty_state"),
                gr.update(value=str(exc), visible=True),
            )
        return (
            data.get("review_markdown", t(language, "no_results")),
            format_papers_markdown(data.get("papers", []), language),
            gr.update(value="", visible=False),
        )

    def update_ui(language: Language):
        return (
            gr.update(value=f"## {t(language, 'review_title')}"),
            gr.update(label=t(language, "review_query_label"), placeholder=t(language, "review_query_placeholder")),
            gr.update(label=t(language, "review_ids_label"), placeholder=t(language, "review_ids_placeholder")),
            gr.update(value=t(language, "review_button")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value=t(language, "empty_state")),
            gr.update(value="", visible=False),
        )

    review_button.click(
        fn=run_review,
        inputs=[lang_selector, query, identifiers],
        outputs=[review_output, papers_output, error_box],
    )
    lang_selector.change(
        fn=update_ui,
        inputs=[lang_selector],
        outputs=[header, query, identifiers, review_button, review_output, papers_output, error_box],
    )
