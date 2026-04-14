"""Crossref research source integration."""

from __future__ import annotations

from typing import Any
import re
from urllib.parse import quote

from agent_core.config import CoreSettings, get_settings
from agent_core.tools.base import BaseResearchHTTPTool
from data.schemas.paper_schema import Paper

_HTML_TAG_RE = re.compile(r"<[^>]+>")


class CrossrefTool(BaseResearchHTTPTool):
    """Async client for Crossref query and DOI lookups."""

    source_name = "crossref"

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        client=None,
    ) -> None:
        super().__init__(settings=settings, client=client)
        self.base_url = self.settings.crossref_base_url

    async def search_papers(self, query: str, *, limit: int = 10) -> list[Paper]:
        """Search Crossref works by query string."""

        payload = await self._request_json(
            "/works",
            params={
                "query": query,
                "rows": min(limit, self.settings.max_results),
            },
        )
        items = payload.get("message", {}).get("items", [])
        return [self._normalize_work(item) for item in items]

    async def get_paper_by_doi(self, doi: str) -> Paper:
        """Fetch a Crossref work by DOI."""

        payload = await self._request_json(f"/works/{quote(doi, safe='')}")
        item = payload.get("message", {})
        return self._normalize_work(item)

    def _normalize_work(self, payload: dict[str, Any]) -> Paper:
        authors = []
        for author in payload.get("author", []):
            full_name = " ".join(
                part.strip()
                for part in [author.get("given", ""), author.get("family", "")]
                if part and part.strip()
            )
            if full_name:
                authors.append(full_name)

        title_values = payload.get("title", [])
        abstract = payload.get("abstract")
        if isinstance(abstract, str):
            abstract = _HTML_TAG_RE.sub("", abstract).strip()

        year = None
        date_parts = payload.get("issued", {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

        primary_url = payload.get("URL")
        links = payload.get("link", [])
        pdf_url = None
        for link in links:
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL")
                break

        return Paper(
            id=payload.get("DOI") or primary_url or "crossref-unknown",
            title=title_values[0] if title_values else "Untitled paper",
            authors=authors,
            year=year,
            abstract=abstract,
            citation_count=None,
            source="crossref",
            url=primary_url,
            pdf_url=pdf_url,
            open_access=True if pdf_url else None,
        )


_DEFAULT_TOOL: CrossrefTool | None = None


def get_tool(settings: CoreSettings | None = None) -> CrossrefTool:
    """Return the default Crossref tool instance."""

    global _DEFAULT_TOOL
    if _DEFAULT_TOOL is None or settings is not None:
        _DEFAULT_TOOL = CrossrefTool(settings=settings or get_settings())
    return _DEFAULT_TOOL


async def search_papers(query: str, *, limit: int = 10) -> list[Paper]:
    """Search Crossref using the default tool instance."""

    return await get_tool().search_papers(query, limit=limit)


async def get_paper_by_doi(doi: str) -> Paper:
    """Fetch a Crossref paper by DOI using the default tool instance."""

    return await get_tool().get_paper_by_doi(doi)
