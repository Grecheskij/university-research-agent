"""Analytics API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_backend_service, require_optional_api_key
from backend.api.mappers import to_paper_out
from backend.api.models.request_models import AnalyticsRequest
from backend.api.models.response_models import AnalyticsResponse
from backend.api.services import ResearchBackendService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/", response_model=AnalyticsResponse, dependencies=[Depends(require_optional_api_key)])
async def get_analytics(
    payload: AnalyticsRequest,
    service: Annotated[ResearchBackendService, Depends(get_backend_service)],
) -> AnalyticsResponse:
    """Return simple analytics over a selected paper set."""

    papers, source_distribution, year_distribution, citation_stats = await service.analytics(payload)
    return AnalyticsResponse(
        papers=[to_paper_out(paper) for paper in papers],
        source_distribution=source_distribution,
        year_distribution=year_distribution,
        citation_stats=citation_stats,
    )
