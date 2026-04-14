"""Mapping helpers between domain models and API response models."""

from __future__ import annotations

from data.schemas.paper_schema import Paper

from backend.api.models.response_models import PaperOut


def to_paper_out(paper: Paper) -> PaperOut:
    """Convert a domain paper model into an API response shape."""

    return PaperOut.model_validate(paper.model_dump())
