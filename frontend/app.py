"""Gradio entrypoint for the bilingual frontend."""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
import os
import sys
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import gradio as gr
import httpx
from dotenv import load_dotenv

load_dotenv()

from backend.api.main import create_app
from frontend.backend_client import create_backend_client
from frontend.components.analytics_tab import build_analytics_tab
from frontend.components.bibliography_tab import build_bibliography_tab
from frontend.components.review_tab import build_review_tab
from frontend.components.search_tab import build_search_tab
from frontend.i18n import Language, get_default_language, t

_BACKEND_THREAD_STARTED = False

CUSTOM_CSS = """
:root {
  --paper-bg: #f4f1ea;
  --panel-bg: rgba(255, 255, 255, 0.88);
  --ink: #1b2a22;
  --accent: #276749;
  --accent-soft: #d7eadf;
  --border: rgba(39, 103, 73, 0.18);
}
.gradio-container {
  background:
    radial-gradient(circle at top left, rgba(215, 234, 223, 0.95), transparent 35%),
    linear-gradient(180deg, #f8f6f1 0%, var(--paper-bg) 100%);
  color: var(--ink);
  font-family: "IBM Plex Sans", "Segoe UI", Tahoma, sans-serif;
}
.app-shell {
  max-width: 1200px;
  margin: 0 auto;
}
.app-hero {
  background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(215, 234, 223, 0.88));
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 1rem 1.25rem;
  box-shadow: 0 20px 60px rgba(26, 57, 44, 0.08);
}
.gr-block, .gr-box, .gr-panel {
  border-radius: 18px !important;
}
.gr-form, .gr-box, .gr-panel, .gr-group {
  background: var(--panel-bg) !important;
  border-color: var(--border) !important;
}
button.primary {
  background: linear-gradient(135deg, #276749, #2f855a) !important;
}
"""


def _should_autostart_backend() -> bool:
    raw_value = os.getenv("AUTO_START_BACKEND", "1").strip().lower()
    return raw_value not in {"0", "false", "no"}


def _is_local_backend_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.hostname in {None, "", "localhost", "127.0.0.1", "0.0.0.0"}


def _start_backend_server() -> None:
    """Start the local FastAPI backend in a daemon thread if needed."""

    global _BACKEND_THREAD_STARTED
    if _BACKEND_THREAD_STARTED:
        return

    backend_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    if not _should_autostart_backend() or not _is_local_backend_url(backend_url):
        return

    try:
        import uvicorn
    except ImportError:
        return

    parsed = urlparse(backend_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000

    def run_server() -> None:
        uvicorn.run(
            create_app(),
            host=host,
            port=port,
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
        )

    thread = Thread(target=run_server, daemon=True)
    thread.start()
    _BACKEND_THREAD_STARTED = True
    _wait_for_backend(backend_url)


def _wait_for_backend(base_url: str) -> None:
    """Wait briefly until the local backend health endpoint responds."""

    for _ in range(20):
        try:
            response = httpx.get(f"{base_url.rstrip('/')}/health", timeout=1.5)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.25)


def create_interface() -> gr.Blocks:
    """Create the Gradio Blocks interface."""

    _start_backend_server()
    backend_client = create_backend_client()
    default_language = get_default_language()

    with gr.Blocks(title="University Research Agent", fill_height=True) as demo:
        with gr.Column(elem_classes=["app-shell"]):
            title_markdown = gr.Markdown(
                f"<div class='app-hero'><h1>{t(default_language, 'app_title')}</h1>"
                f"<p>{t(default_language, 'app_intro')}</p></div>"
            )
            with gr.Row():
                lang_selector = gr.Radio(
                    choices=[("RU", "ru"), ("EN", "en")],
                    value=default_language,
                    label=t(default_language, "language_label"),
                    scale=1,
                )
                backend_status = gr.Markdown(
                    t(default_language, "backend_status").format(url=backend_client.base_url)
                )

            with gr.Tab(t(default_language, "tab_search")):
                build_search_tab(lang_selector, backend_client, default_language)
            with gr.Tab(t(default_language, "tab_review")):
                build_review_tab(lang_selector, backend_client, default_language)
            with gr.Tab(t(default_language, "tab_bibliography")):
                build_bibliography_tab(lang_selector, backend_client, default_language)
            with gr.Tab(t(default_language, "tab_analytics")):
                build_analytics_tab(lang_selector, backend_client, default_language)

        def update_app_shell(language: Language):
            return (
                gr.update(
                    value=(
                        f"<div class='app-hero'><h1>{t(language, 'app_title')}</h1>"
                        f"<p>{t(language, 'app_intro')}</p></div>"
                    )
                ),
                gr.update(label=t(language, "language_label")),
                gr.update(value=t(language, "backend_status").format(url=backend_client.base_url)),
            )

        lang_selector.change(
            fn=update_app_shell,
            inputs=[lang_selector],
            outputs=[title_markdown, lang_selector, backend_status],
        )

    demo.css = CUSTOM_CSS
    return demo


demo = create_interface()


if __name__ == "__main__":
    demo.launch(
        server_name=os.getenv("FRONTEND_HOST", "0.0.0.0"),
        server_port=int(os.getenv("FRONTEND_PORT", "7860")),
        show_error=True,
    )
