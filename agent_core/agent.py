"""Main ReAct-style orchestration for the research assistant."""

from __future__ import annotations

import asyncio
from typing import Literal
import re

from pydantic import BaseModel, Field

from agent_core.chains.bibliography_chain import BibliographyChain, BibliographyResult
from agent_core.chains.review_chain import ReviewChain, ReviewResult
from agent_core.chains.summary_chain import SummaryChain, SummaryResult
from agent_core.config import CoreSettings, get_settings
from agent_core.language import SupportedLanguage, resolve_language
from agent_core.llm import create_chat_model
from agent_core.tools import arxiv_tool, crossref, open_alex, semantic_scholar, unpaywall
from agent_core.tools.base import ResearchToolError
from data.schemas.paper_schema import Paper
from data.vector_store.chroma_manager import ChromaManager

AgentIntent = Literal["review", "summary", "bibliography"]
_DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


class AgentResponse(BaseModel):
    """Structured agent response for later FastAPI integration."""

    intent: AgentIntent
    language: SupportedLanguage
    answer: str
    papers: list[Paper] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    review: ReviewResult | None = None
    summary: SummaryResult | None = None
    bibliography: BibliographyResult | None = None


class ResearchAgent:
    """Coordinate external tools, vector search, and synthesis chains."""

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        llm=None,
        vector_store: ChromaManager | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or create_chat_model(self.settings)
        self.vector_store = vector_store or ChromaManager(settings=self.settings)
        self.semantic_scholar_tool = semantic_scholar.SemanticScholarTool(settings=self.settings)
        self.openalex_tool = open_alex.OpenAlexTool(settings=self.settings)
        self.crossref_tool = crossref.CrossrefTool(settings=self.settings)
        self.arxiv_tool = arxiv_tool.ArxivTool(settings=self.settings)
        self.unpaywall_tool = unpaywall.UnpaywallTool(settings=self.settings)
        self.review_chain = ReviewChain(llm=self.llm, vector_store=self.vector_store)
        self.summary_chain = SummaryChain(llm=self.llm, vector_store=self.vector_store)
        self.bibliography_chain = BibliographyChain(llm=self.llm)

    async def respond(
        self,
        query: str,
        *,
        papers: list[Paper] | None = None,
        target_language: SupportedLanguage | None = None,
    ) -> AgentResponse:
        """Process a user query and return a structured response."""

        language = resolve_language(query, target_language)
        intent = self._classify_intent(query)
        reasoning_steps = [
            f"Detected language: {language}",
            f"Resolved intent: {intent}",
        ]

        source_papers = papers or await self._collect_papers(query)
        if source_papers:
            self.vector_store.add_papers(source_papers)
            reasoning_steps.append(f"Collected {len(source_papers)} source papers")

        rag_papers = self.vector_store.search(query, limit=3)
        combined_papers = self._merge_papers([*source_papers, *rag_papers])
        if rag_papers:
            reasoning_steps.append(f"Recovered {len(rag_papers)} supporting papers from Chroma")

        if intent == "review":
            review = await self.review_chain.run(combined_papers, query, target_language=language)
            return AgentResponse(
                intent=intent,
                language=language,
                answer=self._render_review(review),
                papers=combined_papers,
                reasoning_steps=reasoning_steps,
                review=review,
            )

        if intent == "bibliography":
            bibliography = await self.bibliography_chain.run(combined_papers, language=language)
            return AgentResponse(
                intent=intent,
                language=language,
                answer=self._render_bibliography(bibliography),
                papers=combined_papers,
                reasoning_steps=reasoning_steps,
                bibliography=bibliography,
            )

        summary = await self.summary_chain.run(combined_papers, query, target_language=language)
        return AgentResponse(
            intent=intent,
            language=language,
            answer=self._render_summary(summary),
            papers=combined_papers,
            reasoning_steps=reasoning_steps,
            summary=summary,
        )

    async def close(self) -> None:
        """Close underlying HTTP clients."""

        await asyncio.gather(
            self.semantic_scholar_tool.close(),
            self.openalex_tool.close(),
            self.crossref_tool.close(),
            self.arxiv_tool.close(),
            self.unpaywall_tool.close(),
        )

    def _classify_intent(self, query: str) -> AgentIntent:
        lowered = query.lower()
        if any(token in lowered for token in ["bibliography", "citation", "apa", "mla", "гост", "библиограф"]):
            return "bibliography"
        if any(token in lowered for token in ["review", "literature review", "обзор", "сравни", "gap"]):
            return "review"
        return "summary"

    async def _collect_papers(self, query: str) -> list[Paper]:
        doi_match = _DOI_RE.search(query)
        if doi_match:
            doi = doi_match.group(0).rstrip(".,)")
            try:
                paper = await self.crossref_tool.get_paper_by_doi(doi)
                enriched = await self.unpaywall_tool.enrich_paper(paper)
                return [enriched]
            except ResearchToolError:
                return []

        per_source_limit = max(2, min(self.settings.max_results, 3))
        results = await asyncio.gather(
            self._safe_search(self.semantic_scholar_tool.search_papers(query, limit=per_source_limit)),
            self._safe_search(self.openalex_tool.search_works(query, limit=per_source_limit)),
            self._safe_search(self.crossref_tool.search_papers(query, limit=per_source_limit)),
            self._safe_search(self.arxiv_tool.search_papers(query, limit=per_source_limit)),
        )
        papers = self._merge_papers([paper for result in results for paper in result])
        enriched = await self.unpaywall_tool.enrich_papers(papers)
        return enriched[: self.settings.max_results]

    async def _safe_search(self, coroutine) -> list[Paper]:
        try:
            return await coroutine
        except ResearchToolError:
            return []

    def _merge_papers(self, papers: list[Paper]) -> list[Paper]:
        unique: dict[tuple[str, str], Paper] = {}
        for paper in papers:
            unique[(paper.source, paper.id)] = paper
        return list(unique.values())

    def _render_review(self, review: ReviewResult) -> str:
        groups = "\n".join(
            f"- {topic}: {', '.join(titles)}" for topic, titles in review.thematic_groups.items()
        )
        comparisons = "\n".join(f"- {item}" for item in review.comparison_points)
        gaps = "\n".join(f"- {item}" for item in review.research_gaps)
        return "\n\n".join(
            [
                review.overview,
                groups or "",
                comparisons or "",
                gaps or "",
            ]
        ).strip()

    def _render_summary(self, summary: SummaryResult) -> str:
        key_results = "\n".join(f"- {item}" for item in summary.key_results)
        future_work = "\n".join(f"- {item}" for item in summary.future_work)
        return "\n\n".join([summary.overview, key_results, future_work]).strip()

    def _render_bibliography(self, bibliography: BibliographyResult) -> str:
        sections = [
            "APA 7\n" + "\n".join(f"- {entry}" for entry in bibliography.apa),
            "MLA 9\n" + "\n".join(f"- {entry}" for entry in bibliography.mla),
            "ГОСТ 7.0.5\n" + "\n".join(f"- {entry}" for entry in bibliography.gost),
        ]
        return "\n\n".join(sections)


def build_default_agent(settings: CoreSettings | None = None) -> ResearchAgent:
    """Create a default research agent instance."""

    return ResearchAgent(settings=settings or get_settings())
