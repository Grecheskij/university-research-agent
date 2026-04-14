"""Shared Pydantic schema for normalized research paper records."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PaperSource = Literal["semantic_scholar", "openalex", "arxiv", "crossref"]


class Paper(BaseModel):
    """Unified paper schema shared across tools, chains, API, and storage."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., description="DOI or external source identifier.")
    title: str = Field(..., description="Paper title.")
    authors: list[str] = Field(..., description="Ordered list of author names.")
    year: int | None = Field(default=None, description="Publication year if available.")
    abstract: str | None = Field(
        default=None,
        description="Paper abstract or summary when provided by the source.",
    )
    citation_count: int | None = Field(
        default=None,
        description="Citation count if available from the upstream source.",
    )
    source: PaperSource = Field(..., description="Normalized upstream data source name.")
    url: str | None = Field(default=None, description="Primary landing page URL.")
    pdf_url: str | None = Field(default=None, description="Direct PDF URL when known.")
    open_access: bool | None = Field(
        default=None,
        description="Whether the paper is known to be open access.",
    )
