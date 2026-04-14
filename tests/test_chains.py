"""Tests for research chains."""

from __future__ import annotations

import pytest

from agent_core.chains.bibliography_chain import BibliographyChain
from agent_core.chains.review_chain import ReviewChain
from agent_core.chains.summary_chain import SummaryChain
from data.schemas.paper_schema import Paper


class StubVectorStore:
    """Small vector-store stub for deterministic chain tests."""

    def __init__(self, papers: list[Paper]) -> None:
        self._papers = papers

    def search(self, query: str, *, limit: int = 3) -> list[Paper]:
        return self._papers[:limit]


def _sample_papers() -> list[Paper]:
    return [
        Paper(
            id="10.1000/abc1",
            title="Neural Retrieval for Scientific Search",
            authors=["Jane Doe", "Alex Smith"],
            year=2024,
            abstract="A retrieval model for scientific document ranking.",
            citation_count=42,
            source="semantic_scholar",
            url="https://example.org/neural-retrieval",
            pdf_url="https://example.org/neural-retrieval.pdf",
            open_access=True,
        ),
        Paper(
            id="W123456",
            title="Evaluation Frameworks for Research Agents",
            authors=["Maria Ivanova"],
            year=2023,
            abstract="An evaluation framework for autonomous research agents.",
            citation_count=13,
            source="openalex",
            url="https://example.org/research-agents",
            pdf_url=None,
            open_access=False,
        ),
    ]


@pytest.mark.asyncio
async def test_review_chain_returns_structured_literature_review() -> None:
    papers = _sample_papers()
    vector_store = StubVectorStore(papers[1:])
    chain = ReviewChain(llm=None, vector_store=vector_store)

    result = await chain.run(papers, "Сделай обзор по research agents", target_language="ru")

    assert result.language == "ru"
    assert result.thematic_groups
    assert result.comparison_points
    assert result.research_gaps
    assert "research agents" in result.overview.lower()


@pytest.mark.asyncio
async def test_summary_chain_returns_key_results_and_future_work() -> None:
    papers = _sample_papers()
    chain = SummaryChain(llm=None, vector_store=StubVectorStore([]))

    result = await chain.run(papers, "Summarize recent research agent work", target_language="en")

    assert result.language == "en"
    assert result.key_results
    assert result.future_work
    assert "relevant sources" in result.overview.lower()


@pytest.mark.asyncio
async def test_bibliography_chain_formats_all_required_styles() -> None:
    papers = _sample_papers()
    chain = BibliographyChain()

    result = await chain.run(papers, language="en")

    assert len(result.apa) == 2
    assert len(result.mla) == 2
    assert len(result.gost) == 2
    assert "Neural Retrieval for Scientific Search" in result.apa[0]
    assert "DOI: 10.1000/abc1" in result.gost[0] or "https://example.org/neural-retrieval" in result.gost[0]
