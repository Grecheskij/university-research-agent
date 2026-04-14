"""Pydantic response models for backend API endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from data.schemas.paper_schema import PaperSource

SupportedLanguage = Literal["ru", "en"]


class PaperOut(BaseModel):
    """Flat paper representation for frontend-friendly JSON responses."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    authors: list[str]
    year: int | None = None
    abstract: str | None = None
    citation_count: int | None = None
    source: PaperSource
    url: str | None = None
    pdf_url: str | None = None
    open_access: bool | None = None


class SearchResponse(BaseModel):
    """Search endpoint response."""

    papers: list[PaperOut] = Field(default_factory=list)
    source_stats: dict[str, int] | None = None


class ReviewResponse(BaseModel):
    """Review endpoint response."""

    review_markdown: str
    papers: list[PaperOut] = Field(default_factory=list)
    thematic_groups: dict[str, list[str]] = Field(default_factory=dict)
    comparison_points: list[str] = Field(default_factory=list)
    research_gaps: list[str] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    """Reserved summary response model for future endpoint support."""

    summary_markdown: str
    papers: list[PaperOut] = Field(default_factory=list)


class BibliographyResponse(BaseModel):
    """Bibliography endpoint response."""

    apa7: list[str] = Field(default_factory=list)
    mla9: list[str] = Field(default_factory=list)
    gost: list[str] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    """Analytics endpoint response."""

    papers: list[PaperOut] = Field(default_factory=list)
    source_distribution: dict[str, int] = Field(default_factory=dict)
    year_distribution: dict[str, int] = Field(default_factory=dict)
    citation_stats: dict[str, float | int | None] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health-check response body."""

    status: str = "ok"


class ErrorResponse(BaseModel):
    """Structured error payload."""

    code: str
    message: str
    details: dict[str, Any] | None = None
