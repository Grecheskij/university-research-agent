"""Service layer bridging FastAPI routes and agent_core."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from statistics import mean
import re

from agent_core.agent import ResearchAgent, build_default_agent
from data.schemas.paper_schema import Paper

from backend.api.errors import AppError
from backend.api.models.request_models import (
    AnalyticsRequest,
    BibliographyRequest,
    ReviewRequest,
    SearchRequest,
)

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class ResearchBackendService:
    """Thin service facade used by backend routes."""

    def __init__(self, *, agent: ResearchAgent | None = None) -> None:
        self.agent = agent or build_default_agent()

    async def close(self) -> None:
        """Close the underlying shared agent."""

        await self.agent.close()

    async def search(self, payload: SearchRequest) -> list[Paper]:
        """Search research papers using the agent-core toolset."""

        papers = await self.agent._collect_papers(payload.query)
        filtered = self._apply_filters(papers, year_from=payload.year_from, year_to=payload.year_to, source=payload.source)
        if filtered:
            self.agent.vector_store.add_papers(filtered)
        return filtered[: payload.limit]

    async def review(self, payload: ReviewRequest):
        """Generate a structured literature review."""

        focused_papers = await self._resolve_papers(
            query=payload.query,
            paper_ids=payload.paper_ids,
            dois=payload.dois,
            limit=payload.limit,
        )
        if not focused_papers:
            raise AppError(
                code="papers_not_found",
                message="No papers were found for the requested review.",
                status_code=404,
            )
        review_result = await self.agent.review_chain.run(
            focused_papers,
            payload.query,
            target_language=payload.language,
        )
        return review_result, self.agent._merge_papers(focused_papers)

    async def bibliography(self, payload: BibliographyRequest):
        """Create bibliography entries for the requested papers."""

        papers = await self._resolve_papers(
            query=payload.query,
            paper_ids=payload.paper_ids,
            dois=payload.dois,
            limit=payload.limit,
        )
        if not papers:
            raise AppError(
                code="papers_not_found",
                message="No papers were found for bibliography generation.",
                status_code=404,
            )
        return await self.agent.bibliography_chain.run(
            papers,
            language=payload.language or "ru",
        )

    async def analytics(self, payload: AnalyticsRequest) -> tuple[list[Paper], dict[str, int], dict[str, int], dict[str, float | int | None]]:
        """Compute simple analytics for the requested set of papers."""

        papers = await self._resolve_papers(
            query=payload.query,
            paper_ids=payload.paper_ids,
            dois=payload.dois,
            limit=payload.limit,
        )
        filtered = self._apply_filters(papers, year_from=payload.year_from, year_to=payload.year_to, source=payload.source)
        if not filtered:
            raise AppError(
                code="papers_not_found",
                message="No papers were found for analytics.",
                status_code=404,
            )

        source_distribution = dict(Counter(paper.source for paper in filtered))
        year_distribution = dict(Counter(str(paper.year) for paper in filtered if paper.year is not None))
        citations = [paper.citation_count for paper in filtered if paper.citation_count is not None]
        citation_stats = {
            "count": len(citations),
            "mean": round(mean(citations), 2) if citations else None,
            "max": max(citations) if citations else None,
        }
        return filtered, source_distribution, year_distribution, citation_stats

    async def _resolve_papers(
        self,
        *,
        query: str | None,
        paper_ids: list[str] | None,
        dois: list[str] | None,
        limit: int,
    ) -> list[Paper]:
        papers: list[Paper] = []
        if query:
            papers.extend(await self.agent._collect_papers(query))
        if paper_ids:
            papers.extend(self._lookup_papers_by_ids(paper_ids))
        if dois:
            papers.extend(await self._fetch_dois(dois))
        merged = self.agent._merge_papers(papers)
        return merged[:limit]

    async def _fetch_dois(self, dois: Iterable[str]) -> list[Paper]:
        papers: list[Paper] = []
        for doi in dois:
            if not _DOI_RE.match(doi):
                continue
            try:
                paper = await self.agent.crossref_tool.get_paper_by_doi(doi)
                paper = await self.agent.unpaywall_tool.enrich_paper(paper)
                papers.append(paper)
            except Exception:
                continue
        if papers:
            self.agent.vector_store.add_papers(papers)
        return papers

    def _lookup_papers_by_ids(self, paper_ids: Iterable[str]) -> list[Paper]:
        keys: list[str] = []
        for paper_id in paper_ids:
            if _DOI_RE.match(paper_id):
                keys.append(f"doi:{paper_id.lower()}")
            else:
                keys.extend(
                    [
                        paper_id,
                        f"semantic_scholar:{paper_id}",
                        f"openalex:{paper_id}",
                        f"crossref:{paper_id}",
                        f"arxiv:{paper_id}",
                    ]
                )

        raw = self.agent.vector_store.collection.get(ids=keys)
        metadatas = raw.get("metadatas", [])
        papers = [self.agent.vector_store._paper_from_metadata(metadata) for metadata in metadatas]
        return self.agent._merge_papers(papers)

    def _apply_filters(
        self,
        papers: list[Paper],
        *,
        year_from: int | None,
        year_to: int | None,
        source: str | None,
    ) -> list[Paper]:
        filtered = papers
        if year_from is not None:
            filtered = [paper for paper in filtered if paper.year is None or paper.year >= year_from]
        if year_to is not None:
            filtered = [paper for paper in filtered if paper.year is None or paper.year <= year_to]
        if source is not None:
            filtered = [paper for paper in filtered if paper.source == source]
        return filtered
