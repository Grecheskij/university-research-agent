"""Search API routes."""

from __future__ import annotations

from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_backend_service
from backend.api.mappers import to_paper_out
from backend.api.models.request_models import SearchRequest
from backend.api.models.response_models import SearchResponse
from backend.api.services import ResearchBackendService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search_papers(
    payload: SearchRequest,
    service: Annotated[ResearchBackendService, Depends(get_backend_service)],
) -> SearchResponse:
    """Search research papers across supported data sources."""

    papers = await service.search(payload)
    source_stats = dict(Counter(paper.source for paper in papers))
    return SearchResponse(
        papers=[to_paper_out(paper) for paper in papers],
        source_stats=source_stats,
    )
