"""Review API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_backend_service
from backend.api.mappers import to_paper_out
from backend.api.models.request_models import ReviewRequest
from backend.api.models.response_models import ReviewResponse
from backend.api.services import ResearchBackendService
from agent_core.chains.review_chain import ReviewResult

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/", response_model=ReviewResponse)
async def generate_review(
    payload: ReviewRequest,
    service: Annotated[ResearchBackendService, Depends(get_backend_service)],
) -> ReviewResponse:
    """Build a literature review for the requested topic or paper set."""

    review_result, papers = await service.review(payload)
    return ReviewResponse(
        review_markdown=_render_review_markdown(review_result),
        papers=[to_paper_out(paper) for paper in papers],
        thematic_groups=review_result.thematic_groups,
        comparison_points=review_result.comparison_points,
        research_gaps=review_result.research_gaps,
    )


def _render_review_markdown(review: ReviewResult) -> str:
    """Serialize a review result into markdown for the frontend."""

    sections = [review.overview]
    if review.thematic_groups:
        sections.append(
            "\n".join(
                f"- {topic}: {', '.join(titles)}"
                for topic, titles in review.thematic_groups.items()
            )
        )
    if review.comparison_points:
        sections.append("\n".join(f"- {item}" for item in review.comparison_points))
    if review.research_gaps:
        sections.append("\n".join(f"- {item}" for item in review.research_gaps))
    return "\n\n".join(section for section in sections if section).strip()
