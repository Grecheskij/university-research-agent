"""OpenAlex research source integration."""

from __future__ import annotations

from typing import Any

from agent_core.config import CoreSettings, get_settings
from agent_core.tools.base import BaseResearchHTTPTool
from data.schemas.paper_schema import Paper


class OpenAlexTool(BaseResearchHTTPTool):
    """Async client for OpenAlex search operations."""

    source_name = "openalex"

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        client=None,
    ) -> None:
        super().__init__(settings=settings, client=client)
        self.base_url = self.settings.openalex_base_url

    async def search_works(self, query: str, *, limit: int = 10) -> list[Paper]:
        """Search OpenAlex works by free-text query."""

        payload = await self._request_json(
            "/works",
            params={
                "search": query,
                "per-page": min(limit, self.settings.max_results),
            },
        )
        return [self._normalize_work(work) for work in payload.get("results", [])]

    def _normalize_work(self, payload: dict[str, Any]) -> Paper:
        authors = [
            authorship.get("author", {}).get("display_name", "").strip()
            for authorship in payload.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        open_access = payload.get("open_access") or {}
        primary_location = payload.get("primary_location") or {}
        best_oa_location = payload.get("best_oa_location") or {}
        identifier = payload.get("doi") or payload.get("id") or "openalex-unknown"
        if isinstance(identifier, str) and identifier.startswith("https://openalex.org/"):
            identifier = identifier.removeprefix("https://openalex.org/")
        return Paper(
            id=identifier,
            title=payload.get("display_name") or "Untitled paper",
            authors=authors,
            year=payload.get("publication_year"),
            abstract=None,
            citation_count=payload.get("cited_by_count"),
            source="openalex",
            url=primary_location.get("landing_page_url") or payload.get("id"),
            pdf_url=best_oa_location.get("pdf_url"),
            open_access=open_access.get("is_oa"),
        )


_DEFAULT_TOOL: OpenAlexTool | None = None


def get_tool(settings: CoreSettings | None = None) -> OpenAlexTool:
    """Return the default OpenAlex tool instance."""

    global _DEFAULT_TOOL
    if _DEFAULT_TOOL is None or settings is not None:
        _DEFAULT_TOOL = OpenAlexTool(settings=settings or get_settings())
    return _DEFAULT_TOOL


async def search_papers(query: str, *, limit: int = 10) -> list[Paper]:
    """Search OpenAlex using the default tool instance."""

    return await get_tool().search_works(query, limit=limit)
