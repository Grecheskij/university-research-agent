"""Tests for FastAPI backend routes."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from agent_core.chains.bibliography_chain import BibliographyResult
from agent_core.chains.review_chain import ReviewResult
from backend.api.config import BackendSettings
from backend.api.main import create_app
from data.schemas.paper_schema import Paper


class FakeBackendService:
    """Small backend service stub used by route tests."""

    def __init__(self) -> None:
        self._papers = [
            Paper(
                id="10.1000/test-1",
                title="Research Agents in Practice",
                authors=["Jane Doe"],
                year=2024,
                abstract="A practical paper about research agents.",
                citation_count=11,
                source="crossref",
                url="https://example.org/paper-1",
                pdf_url="https://example.org/paper-1.pdf",
                open_access=True,
            )
        ]

    async def close(self) -> None:
        return None

    async def search(self, payload) -> list[Paper]:
        assert payload.query
        return self._papers

    async def review(self, payload):
        review = ReviewResult(
            language=payload.language or "ru",
            overview="Structured review overview.",
            thematic_groups={"Agents": ["Research Agents in Practice"]},
            comparison_points=["Comparison point."],
            research_gaps=["Gap point."],
            referenced_titles=[paper.title for paper in self._papers],
        )
        return review, self._papers

    async def bibliography(self, payload):
        return BibliographyResult(
            language=payload.language or "ru",
            apa=["Doe, J. (2024). Research Agents in Practice. https://example.org/paper-1"],
            mla=['Doe, Jane. "Research Agents in Practice." Crossref, 2024, https://example.org/paper-1'],
            gost=["Doe J. Research Agents in Practice // crossref. 2024. https://example.org/paper-1"],
        )

    async def analytics(self, payload):
        return self._papers, {"crossref": 1}, {"2024": 1}, {"count": 1, "mean": 11.0, "max": 11}


def _settings() -> BackendSettings:
    return BackendSettings(
        app_name="Test API",
        app_description="Backend API tests",
        app_version="0.2.0",
        frontend_origins=["http://localhost:7860"],
        api_key=None,
        max_request_bytes=1024 * 1024,
    )


@pytest.mark.asyncio
async def test_healthcheck_returns_ok() -> None:
    app = create_app(settings=_settings(), research_service=FakeBackendService())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_search_endpoint_returns_search_response_shape() -> None:
    app = create_app(settings=_settings(), research_service=FakeBackendService())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/search/", json={"query": "research agents", "limit": 5})

    body = response.json()
    assert response.status_code == 200
    assert len(body["papers"]) == 1
    assert body["papers"][0]["title"] == "Research Agents in Practice"
    assert body["source_stats"]["crossref"] == 1


@pytest.mark.asyncio
async def test_review_endpoint_returns_markdown_and_papers() -> None:
    app = create_app(settings=_settings(), research_service=FakeBackendService())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/review/", json={"query": "literature review on research agents"})

    body = response.json()
    assert response.status_code == 200
    assert "Structured review overview." in body["review_markdown"]
    assert "Agents: Research Agents in Practice" in body["review_markdown"]
    assert body["thematic_groups"]["Agents"] == ["Research Agents in Practice"]
    assert body["papers"][0]["id"] == "10.1000/test-1"


@pytest.mark.asyncio
async def test_bibliography_endpoint_returns_three_styles() -> None:
    app = create_app(settings=_settings(), research_service=FakeBackendService())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/bibliography/", json={"query": "research agents"})

    body = response.json()
    assert response.status_code == 200
    assert len(body["apa7"]) == 1
    assert len(body["mla9"]) == 1
    assert len(body["gost"]) == 1


@pytest.mark.asyncio
async def test_analytics_endpoint_returns_distribution_payload() -> None:
    app = create_app(settings=_settings(), research_service=FakeBackendService())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/analytics/", json={"query": "research agents"})

    body = response.json()
    assert response.status_code == 200
    assert body["source_distribution"] == {"crossref": 1}
    assert body["year_distribution"] == {"2024": 1}
    assert body["citation_stats"]["max"] == 11


@pytest.mark.asyncio
async def test_validation_errors_return_structured_payload() -> None:
    app = create_app(settings=_settings(), research_service=FakeBackendService())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/search/", json={"query": "hi"})

    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "validation_error"
    assert "errors" in body["details"]
