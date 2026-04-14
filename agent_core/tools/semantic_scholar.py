"""Semantic Scholar research source integration."""

from __future__ import annotations

import asyncio
from typing import Any

from agent_core.config import CoreSettings, get_settings
from agent_core.tools.base import BaseResearchHTTPTool
from data.schemas.paper_schema import Paper


class SemanticScholarTool(BaseResearchHTTPTool):
    """Async client for Semantic Scholar search operations."""

    source_name = "semantic_scholar"

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        client=None,
    ) -> None:
        super().__init__(settings=settings, client=client)
        self.base_url = self.settings.semantic_scholar_base_url

    def _default_headers(self) -> dict[str, str]:
        headers = super()._default_headers()
        api_key = self.settings.semantic_scholar_api_key
        if api_key:
            headers["x-api-key"] = api_key
        return headers

    async def _after_request(self) -> None:
        """Respect Semantic Scholar's documented rate limit."""

        await asyncio.sleep(1)

    async def search_papers(self, query: str, *, limit: int = 10) -> list[Paper]:
        """Search Semantic Scholar papers by free-text query."""

        payload = await self._request_json(
            "/paper/search",
            params={
                "query": query,
                "limit": min(limit, self.settings.max_results),
                "fields": ",".join(
                    [
                        "paperId",
                        "externalIds",
                        "title",
                        "authors",
                        "year",
                        "abstract",
                        "citationCount",
                        "url",
                        "isOpenAccess",
                        "openAccessPdf",
                    ]
                ),
            },
        )
        papers = payload.get("data", [])
        return [self._normalize_paper(item) for item in papers]

    async def get_paper(self, paper_id: str) -> Paper:
        """Fetch a single paper by Semantic Scholar identifier."""

        payload = await self._request_json(
            f"/paper/{paper_id}",
            params={
                "fields": ",".join(
                    [
                        "paperId",
                        "externalIds",
                        "title",
                        "authors",
                        "year",
                        "abstract",
                        "citationCount",
                        "url",
                        "isOpenAccess",
                        "openAccessPdf",
                    ]
                )
            },
        )
        return self._normalize_paper(payload)

    def _normalize_paper(self, payload: dict[str, Any]) -> Paper:
        external_ids = payload.get("externalIds") or {}
        doi = external_ids.get("DOI")
        authors = [
            author.get("name", "").strip()
            for author in payload.get("authors", [])
            if author.get("name")
        ]
        open_access_pdf = payload.get("openAccessPdf") or {}
        pdf_url = open_access_pdf.get("url")
        is_open_access = payload.get("isOpenAccess")
        if is_open_access is None and pdf_url:
            is_open_access = True
        return Paper(
            id=doi or payload.get("paperId") or payload.get("url") or "semantic-scholar-unknown",
            title=payload.get("title") or "Untitled paper",
            authors=authors,
            year=payload.get("year"),
            abstract=payload.get("abstract"),
            citation_count=payload.get("citationCount"),
            source="semantic_scholar",
            url=payload.get("url"),
            pdf_url=pdf_url,
            open_access=is_open_access,
        )


_DEFAULT_TOOL: SemanticScholarTool | None = None


def get_tool(settings: CoreSettings | None = None) -> SemanticScholarTool:
    """Return the default Semantic Scholar tool instance."""

    global _DEFAULT_TOOL
    if _DEFAULT_TOOL is None or settings is not None:
        _DEFAULT_TOOL = SemanticScholarTool(settings=settings or get_settings())
    return _DEFAULT_TOOL


async def search_papers(query: str, *, limit: int = 10) -> list[Paper]:
    """Search Semantic Scholar using the default tool instance."""

    return await get_tool().search_papers(query, limit=limit)
