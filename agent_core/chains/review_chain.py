"""Literature review chain implementation."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
import re

from pydantic import BaseModel, Field

from agent_core.language import SupportedLanguage, resolve_language
from agent_core.llm import extract_text
from agent_core.prompts.review_prompt import get_review_prompt
from data.schemas.paper_schema import Paper

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "using",
    "based",
    "study",
    "analysis",
    "system",
    "approach",
    "research",
    "into",
    "about",
    "обзор",
    "анализ",
    "исследование",
    "метод",
    "подход",
    "система",
    "данных",
    "using",
}
_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]{4,}")


class ReviewResult(BaseModel):
    """Structured output for the literature review chain."""

    language: SupportedLanguage
    overview: str
    thematic_groups: dict[str, list[str]] = Field(default_factory=dict)
    comparison_points: list[str] = Field(default_factory=list)
    research_gaps: list[str] = Field(default_factory=list)
    referenced_titles: list[str] = Field(default_factory=list)


class ReviewChain:
    """Create structured literature reviews from a set of papers."""

    def __init__(self, *, llm: Any | None = None, vector_store: Any | None = None) -> None:
        self.llm = llm
        self.vector_store = vector_store

    async def run(
        self,
        papers: list[Paper],
        user_query: str,
        *,
        target_language: SupportedLanguage | None = None,
    ) -> ReviewResult:
        """Build a literature review for the supplied papers and query."""

        language = resolve_language(user_query, target_language)
        rag_papers = []
        if self.vector_store is not None:
            rag_papers = self.vector_store.search(user_query, limit=3)

        combined = _merge_papers([*papers, *rag_papers])
        thematic_groups = _group_papers(combined, language)
        comparison_points = _build_comparison_points(combined, language)
        research_gaps = _build_research_gaps(combined, language)
        overview = await self._build_overview(
            combined,
            rag_papers,
            thematic_groups,
            comparison_points,
            research_gaps,
            user_query,
            language,
        )

        return ReviewResult(
            language=language,
            overview=overview,
            thematic_groups=thematic_groups,
            comparison_points=comparison_points,
            research_gaps=research_gaps,
            referenced_titles=[paper.title for paper in combined],
        )

    async def _build_overview(
        self,
        papers: list[Paper],
        rag_papers: list[Paper],
        thematic_groups: dict[str, list[str]],
        comparison_points: list[str],
        research_gaps: list[str],
        user_query: str,
        language: SupportedLanguage,
    ) -> str:
        prompt = get_review_prompt(language)
        if self.llm is not None and prompt is not None:
            prompt_value = prompt.invoke(
                {
                    "user_query": user_query,
                    "papers_context": _papers_context(papers),
                    "rag_context": _papers_context(rag_papers),
                }
            )
            result = await self.llm.ainvoke(prompt_value.to_messages())
            return extract_text(result)

        if language == "ru":
            opening = (
                f"По запросу «{user_query}» отобрано {len(papers)} релевантных работ. "
                f"Основные тематические кластеры: {', '.join(thematic_groups) or 'единое направление'}."
            )
        else:
            opening = (
                f"For the query '{user_query}', {len(papers)} relevant papers were selected. "
                f"Main thematic clusters: {', '.join(thematic_groups) or 'a single research track'}."
            )

        comparison_text = " ".join(comparison_points[:2])
        gap_text = " ".join(research_gaps[:2])
        return " ".join(part for part in [opening, comparison_text, gap_text] if part).strip()


def _merge_papers(papers: list[Paper]) -> list[Paper]:
    unique: dict[tuple[str, str], Paper] = {}
    for paper in papers:
        unique[(paper.source, paper.id)] = paper
    return list(unique.values())


def _topic_from_paper(paper: Paper, language: SupportedLanguage) -> str:
    tokens = [match.group(0).lower() for match in _WORD_RE.finditer(f"{paper.title} {paper.abstract or ''}")]
    for token in tokens:
        if token not in _STOPWORDS:
            return token.capitalize()
    return "Общая тема" if language == "ru" else "General Topic"


def _group_papers(papers: list[Paper], language: SupportedLanguage) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for paper in papers:
        grouped[_topic_from_paper(paper, language)].append(paper.title)
    return dict(grouped)


def _build_comparison_points(papers: list[Paper], language: SupportedLanguage) -> list[str]:
    if not papers:
        return []

    highest_cited = max(papers, key=lambda paper: paper.citation_count or 0)
    newest = max(papers, key=lambda paper: paper.year or 0)
    if language == "ru":
        return [
            f"Наиболее цитируемая работа: «{highest_cited.title}» ({highest_cited.citation_count or 0} цитирований).",
            f"Самая новая публикация: «{newest.title}» ({newest.year or 'год не указан'}).",
        ]
    return [
        f"The most cited paper is '{highest_cited.title}' ({highest_cited.citation_count or 0} citations).",
        f"The most recent publication is '{newest.title}' ({newest.year or 'year unavailable'}).",
    ]


def _build_research_gaps(papers: list[Paper], language: SupportedLanguage) -> list[str]:
    if not papers:
        return []

    missing_abstracts = sum(1 for paper in papers if not paper.abstract)
    closed_access = sum(1 for paper in papers if paper.open_access is False)
    if language == "ru":
        gaps = [
            f"У {missing_abstracts} работ отсутствует аннотация, что ограничивает сравнение методологии."
        ]
        if closed_access:
            gaps.append(
                f"Как минимум {closed_access} источников недоступны в открытом доступе, что затрудняет воспроизводимость."
            )
        gaps.append("Поле выигрывает от более явного сопоставления тем, данных и ограничений между работами.")
        return gaps

    gaps = [
        f"{missing_abstracts} papers do not expose abstracts, which limits methodological comparison."
    ]
    if closed_access:
        gaps.append(
            f"At least {closed_access} sources are not openly accessible, making reproducibility harder."
        )
    gaps.append("The field would benefit from clearer cross-paper comparisons of datasets, methods, and limitations.")
    return gaps


def _papers_context(papers: list[Paper]) -> str:
    lines = []
    for paper in papers:
        lines.append(
            f"- {paper.title} | authors={', '.join(paper.authors) or 'n/a'} | "
            f"year={paper.year or 'n/a'} | source={paper.source} | citations={paper.citation_count}"
        )
    return "\n".join(lines) or "- no papers"
