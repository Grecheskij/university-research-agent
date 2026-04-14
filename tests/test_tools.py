"""Tests for external research tools."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from agent_core.config import CoreSettings
from agent_core.tools.arxiv_tool import ArxivTool
from agent_core.tools.crossref import CrossrefTool
from agent_core.tools.open_alex import OpenAlexTool
from agent_core.tools.semantic_scholar import SemanticScholarTool
from agent_core.tools.unpaywall import UnpaywallTool
from agent_core.tools.base import ResearchToolError
from data.schemas.paper_schema import Paper


def _settings() -> CoreSettings:
    return CoreSettings(
        semantic_scholar_base_url="https://semantic.example",
        openalex_base_url="https://openalex.example",
        crossref_base_url="https://crossref.example",
        arxiv_base_url="https://arxiv.example",
        unpaywall_base_url="https://unpaywall.example",
        semantic_scholar_api_key=None,
        unpaywall_email="research@example.com",
        contact_email="research@example.com",
        gemini_api_key=None,
        groq_api_key=None,
        gemini_model="gemini-2.0-flash",
        groq_model="llama-3.3-70b-versatile",
        chroma_path=Path(".test-chroma"),
        chroma_collection_name="research_papers",
        sentence_transformer_model="all-MiniLM-L6-v2",
        request_timeout=30.0,
        max_results=10,
        retry_attempts=2,
        retry_min_seconds=0.01,
        retry_max_seconds=0.02,
    )


def _client(base_url: str, handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(base_url=base_url, transport=transport, timeout=30)


@pytest.mark.asyncio
async def test_semantic_scholar_search_returns_normalized_papers() -> None:
    settings = _settings()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/paper/search"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "paperId": "abc123",
                        "externalIds": {"DOI": "10.1000/xyz123"},
                        "title": "Transformer Research",
                        "authors": [{"name": "Jane Doe"}, {"name": "John Roe"}],
                        "year": 2024,
                        "abstract": "Study of transformers",
                        "citationCount": 18,
                        "url": "https://example.org/paper",
                        "isOpenAccess": True,
                        "openAccessPdf": {"url": "https://example.org/paper.pdf"},
                    }
                ]
            },
        )

    async with _client(settings.semantic_scholar_base_url, handler) as client:
        tool = SemanticScholarTool(settings=settings, client=client)
        papers = await tool.search_papers("transformers")

    assert len(papers) == 1
    assert papers[0].id == "10.1000/xyz123"
    assert papers[0].citation_count == 18
    assert papers[0].open_access is True


@pytest.mark.asyncio
async def test_openalex_search_maps_open_access_metadata() -> None:
    settings = _settings()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/works"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "display_name": "Retrieval Augmented Generation",
                        "authorships": [{"author": {"display_name": "Alex Smith"}}],
                        "publication_year": 2023,
                        "cited_by_count": 9,
                        "open_access": {"is_oa": True},
                        "primary_location": {"landing_page_url": "https://openalex.org/W123"},
                        "best_oa_location": {"pdf_url": "https://example.org/rag.pdf"},
                    }
                ]
            },
        )

    async with _client(settings.openalex_base_url, handler) as client:
        tool = OpenAlexTool(settings=settings, client=client)
        papers = await tool.search_works("rag")

    assert papers[0].id == "W123"
    assert papers[0].pdf_url == "https://example.org/rag.pdf"
    assert papers[0].open_access is True


@pytest.mark.asyncio
async def test_crossref_invalid_json_raises_research_tool_error() -> None:
    settings = _settings()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    async with _client(settings.crossref_base_url, handler) as client:
        tool = CrossrefTool(settings=settings, client=client)
        with pytest.raises(ResearchToolError, match="invalid JSON"):
            await tool.search_papers("graph neural networks")


@pytest.mark.asyncio
async def test_arxiv_invalid_xml_raises_research_tool_error() -> None:
    settings = _settings()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-xml")

    async with _client(settings.arxiv_base_url, handler) as client:
        tool = ArxivTool(settings=settings, client=client)
        with pytest.raises(ResearchToolError, match="invalid Atom XML"):
            await tool.search_papers("agents")


@pytest.mark.asyncio
async def test_unpaywall_enriches_existing_paper() -> None:
    settings = _settings()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["email"] == "research@example.com"
        return httpx.Response(
            200,
            json={
                "is_oa": True,
                "best_oa_location": {
                    "url": "https://publisher.example/paper",
                    "url_for_pdf": "https://publisher.example/paper.pdf",
                },
                "oa_locations": [],
            },
        )

    paper = Paper(
        id="10.1000/xyz123",
        title="Open Access Paper",
        authors=["Jane Doe"],
        year=2024,
        abstract=None,
        citation_count=None,
        source="crossref",
        url=None,
        pdf_url=None,
        open_access=None,
    )

    async with _client(settings.unpaywall_base_url, handler) as client:
        tool = UnpaywallTool(settings=settings, client=client)
        enriched = await tool.enrich_paper(paper)

    assert enriched.pdf_url == "https://publisher.example/paper.pdf"
    assert enriched.url == "https://publisher.example/paper"
    assert enriched.open_access is True
