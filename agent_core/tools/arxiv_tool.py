"""arXiv research source integration."""

from __future__ import annotations

from typing import Any

import feedparser

from agent_core.config import CoreSettings, get_settings
from agent_core.tools.base import BaseResearchHTTPTool, ResearchToolError
from data.schemas.paper_schema import Paper


class ArxivTool(BaseResearchHTTPTool):
    """Async client for arXiv Atom API operations."""

    source_name = "arxiv"

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        client=None,
    ) -> None:
        super().__init__(settings=settings, client=client)
        self.base_url = self.settings.arxiv_base_url

    def _default_headers(self) -> dict[str, str]:
        headers = super()._default_headers()
        headers["Accept"] = "application/atom+xml"
        return headers

    async def search_papers(self, query: str, *, limit: int = 10) -> list[Paper]:
        """Search arXiv preprints by query string."""

        response_text = await self._request_text(
            "/query",
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(limit, self.settings.max_results),
            },
        )
        feed = feedparser.parse(response_text)
        if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
            raise ResearchToolError("arXiv returned invalid Atom XML")
        return [self._normalize_entry(entry) for entry in feed.entries]

    def _normalize_entry(self, payload: Any) -> Paper:
        authors = [
            author.get("name", "").strip()
            for author in payload.get("authors", [])
            if author.get("name")
        ]
        raw_id = payload.get("id", "")
        arxiv_id = raw_id.rsplit("/", maxsplit=1)[-1] if raw_id else "arxiv-unknown"
        published = payload.get("published", "")
        year = int(published[:4]) if published[:4].isdigit() else None
        pdf_url = None
        for link in payload.get("links", []):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href")
                break

        return Paper(
            id=arxiv_id,
            title=(payload.get("title") or "Untitled paper").replace("\n", " ").strip(),
            authors=authors,
            year=year,
            abstract=(payload.get("summary") or "").replace("\n", " ").strip() or None,
            citation_count=None,
            source="arxiv",
            url=raw_id or payload.get("link"),
            pdf_url=pdf_url,
            open_access=True,
        )


_DEFAULT_TOOL: ArxivTool | None = None


def get_tool(settings: CoreSettings | None = None) -> ArxivTool:
    """Return the default arXiv tool instance."""

    global _DEFAULT_TOOL
    if _DEFAULT_TOOL is None or settings is not None:
        _DEFAULT_TOOL = ArxivTool(settings=settings or get_settings())
    return _DEFAULT_TOOL


async def search_papers(query: str, *, limit: int = 10) -> list[Paper]:
    """Search arXiv using the default tool instance."""

    return await get_tool().search_papers(query, limit=limit)
