"""Pydantic request models for backend API endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from data.schemas.paper_schema import PaperSource

SupportedLanguage = Literal["ru", "en"]


class BaseRequestModel(BaseModel):
    """Shared request validation settings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchRequest(BaseRequestModel):
    """Request payload for paper search."""

    query: str = Field(..., min_length=3, max_length=1_000)
    language: SupportedLanguage | None = None
    limit: int = Field(default=10, ge=1, le=10)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    year_to: int | None = Field(default=None, ge=1900, le=2100)
    source: PaperSource | None = None


class ReviewRequest(BaseRequestModel):
    """Request payload for literature review generation."""

    query: str = Field(..., min_length=3, max_length=1_500)
    language: SupportedLanguage | None = None
    paper_ids: list[str] | None = Field(default=None, max_length=10)
    dois: list[str] | None = Field(default=None, max_length=10)
    limit: int = Field(default=10, ge=1, le=10)


class SummaryRequest(BaseRequestModel):
    """Reserved request model for future summary endpoint support."""

    query: str | None = Field(default=None, min_length=3, max_length=1_000)
    paper_ids: list[str] | None = Field(default=None, max_length=10)
    language: SupportedLanguage | None = None

    @model_validator(mode="after")
    def validate_query_or_papers(self) -> "SummaryRequest":
        """Require either a query or explicit paper identifiers."""

        if not self.query and not self.paper_ids:
            raise ValueError("Either query or paper_ids must be provided.")
        return self


class BibliographyRequest(BaseRequestModel):
    """Request payload for bibliography generation."""

    query: str | None = Field(default=None, min_length=3, max_length=1_000)
    paper_ids: list[str] | None = Field(default=None, max_length=10)
    dois: list[str] | None = Field(default=None, max_length=10)
    language: SupportedLanguage | None = None
    limit: int = Field(default=10, ge=1, le=10)

    @model_validator(mode="after")
    def validate_input_presence(self) -> "BibliographyRequest":
        """Require at least one source of paper selection."""

        if not self.query and not self.paper_ids and not self.dois:
            raise ValueError("At least one of query, paper_ids, or dois must be provided.")
        return self


class AnalyticsRequest(BaseRequestModel):
    """Request payload for simple paper analytics."""

    query: str | None = Field(default=None, min_length=3, max_length=1_000)
    paper_ids: list[str] | None = Field(default=None, max_length=10)
    dois: list[str] | None = Field(default=None, max_length=10)
    language: SupportedLanguage | None = None
    limit: int = Field(default=10, ge=1, le=10)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    year_to: int | None = Field(default=None, ge=1900, le=2100)
    source: PaperSource | None = None

    @model_validator(mode="after")
    def validate_input_presence(self) -> "AnalyticsRequest":
        """Require a query or explicit identifiers for analytics."""

        if not self.query and not self.paper_ids and not self.dois:
            raise ValueError("At least one of query, paper_ids, or dois must be provided.")
        return self
