"""Bibliography API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_backend_service
from backend.api.models.request_models import BibliographyRequest
from backend.api.models.response_models import BibliographyResponse
from backend.api.services import ResearchBackendService

router = APIRouter(prefix="/api/bibliography", tags=["bibliography"])


@router.post("/", response_model=BibliographyResponse)
async def generate_bibliography(
    payload: BibliographyRequest,
    service: Annotated[ResearchBackendService, Depends(get_backend_service)],
) -> BibliographyResponse:
    """Generate bibliography entries in APA, MLA, and GOST formats."""

    bibliography = await service.bibliography(payload)
    return BibliographyResponse(
        apa7=bibliography.apa,
        mla9=bibliography.mla,
        gost=bibliography.gost,
    )
