"""Root entrypoint for local Gradio launch and Hugging Face Spaces."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env", override=True)

from frontend.app import demo


if __name__ == "__main__":
    demo.launch(
        server_name=os.getenv("FRONTEND_HOST", "0.0.0.0"),
        server_port=int(os.getenv("FRONTEND_PORT", "7860")),
        show_error=True,
    )
