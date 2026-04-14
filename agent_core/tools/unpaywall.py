"""Unpaywall open-access enrichment integration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import quote

from agent_core.config import CoreSettings, get_settings
from agent_core.tools.base import BaseResearchHTTPTool, ResearchToolError
from data.schemas.paper_schema import Paper


class UnpaywallTool(BaseResearchHTTPTool):
    """Async client for enriching DOI-based papers with open-access metadata."""

    source_name = "unpaywall"

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        client=None,
    ) -> None:
        super().__init__(settings=settings, client=client)
        self.base_url = self.settings.unpaywall_base_url

    async def enrich_paper(self, paper: Paper) -> Paper:
        """Return a paper enriched with Unpaywall open-access metadata."""

        if not self._looks_like_doi(paper.id):
            return paper
        if not self.settings.unpaywall_email:
            return paper

        try:
            payload = await self._request_json(
                f"/{quote(paper.id, safe='')}",
                params={"email": self.settings.unpaywall_email},
            )
        except ResearchToolError as exc:
            if "status 404" in str(exc):
                return paper
            raise

        return self._merge_open_access_metadata(paper, payload)

    async def enrich_papers(self, papers: Iterable[Paper]) -> list[Paper]:
        """Enrich a list of papers with open-access metadata."""

        return [await self.enrich_paper(paper) for paper in papers]

    def _merge_open_access_metadata(self, paper: Paper, payload: dict[str, Any]) -> Paper:
        best_oa = payload.get("best_oa_location") or {}
        oa_locations = payload.get("oa_locations") or []
        pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
        if pdf_url is None:
            for location in oa_locations:
                pdf_url = location.get("url_for_pdf") or location.get("url")
                if pdf_url:
                    break

        open_access = payload.get("is_oa")
        if open_access is None and pdf_url:
            open_access = True

        canonical_url = best_oa.get("url") or paper.url
        return paper.model_copy(
            update={
                "url": canonical_url,
                "pdf_url": pdf_url or paper.pdf_url,
                "open_access": open_access if open_access is not None else paper.open_access,
            }
        )

    def _looks_like_doi(self, identifier: str) -> bool:
        return identifier.startswith("10.") and "/" in identifier


_DEFAULT_TOOL: UnpaywallTool | None = None


def get_tool(settings: CoreSettings | None = None) -> UnpaywallTool:
    """Return the default Unpaywall tool instance."""

    global _DEFAULT_TOOL
    if _DEFAULT_TOOL is None or settings is not None:
        _DEFAULT_TOOL = UnpaywallTool(settings=settings or get_settings())
    return _DEFAULT_TOOL


async def enrich_paper(paper: Paper) -> Paper:
    """Enrich a single paper with open-access metadata."""

    return await get_tool().enrich_paper(paper)


async def enrich_papers(papers: Iterable[Paper]) -> list[Paper]:
    """Enrich multiple papers with open-access metadata."""

    return await get_tool().enrich_papers(papers)
