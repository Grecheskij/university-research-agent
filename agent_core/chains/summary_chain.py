"""Research summary chain implementation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_core.language import SupportedLanguage, resolve_language
from agent_core.llm import extract_text
from agent_core.prompts.analysis_prompt import get_summary_prompt
from data.schemas.paper_schema import Paper


class SummaryResult(BaseModel):
    """Structured output for summary synthesis."""

    language: SupportedLanguage
    overview: str
    key_results: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    referenced_titles: list[str] = Field(default_factory=list)


class SummaryChain:
    """Summarize a collection of research papers."""

    def __init__(self, *, llm: Any | None = None, vector_store: Any | None = None) -> None:
        self.llm = llm
        self.vector_store = vector_store

    async def run(
        self,
        papers: list[Paper],
        user_query: str,
        *,
        target_language: SupportedLanguage | None = None,
    ) -> SummaryResult:
        """Summarize research papers for the user's question."""

        language = resolve_language(user_query, target_language)
        rag_papers = []
        if self.vector_store is not None:
            rag_papers = self.vector_store.search(user_query, limit=3)

        combined = _merge_papers([*papers, *rag_papers])
        key_results = _build_key_results(combined, language)
        future_work = _build_future_work(combined, language)
        overview = await self._build_overview(
            combined,
            rag_papers,
            key_results,
            future_work,
            user_query,
            language,
        )
        return SummaryResult(
            language=language,
            overview=overview,
            key_results=key_results,
            future_work=future_work,
            referenced_titles=[paper.title for paper in combined],
        )

    async def _build_overview(
        self,
        papers: list[Paper],
        rag_papers: list[Paper],
        key_results: list[str],
        future_work: list[str],
        user_query: str,
        language: SupportedLanguage,
    ) -> str:
        prompt = get_summary_prompt(language)
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
            lead = (
                f"По запросу «{user_query}» видно, что корпус работ сходится вокруг "
                f"{len(papers)} релевантных источников и общих исследовательских мотивов."
            )
        else:
            lead = (
                f"For the query '{user_query}', the paper set converges around "
                f"{len(papers)} relevant sources and shared research directions."
            )
        return " ".join([lead, key_results[0] if key_results else "", future_work[0] if future_work else ""]).strip()


def _merge_papers(papers: list[Paper]) -> list[Paper]:
    unique: dict[tuple[str, str], Paper] = {}
    for paper in papers:
        unique[(paper.source, paper.id)] = paper
    return list(unique.values())


def _build_key_results(papers: list[Paper], language: SupportedLanguage) -> list[str]:
    if not papers:
        return []

    highest_cited = max(papers, key=lambda paper: paper.citation_count or 0)
    open_access_count = sum(1 for paper in papers if paper.open_access)
    if language == "ru":
        return [
            f"Самая влиятельная работа в наборе — «{highest_cited.title}».",
            f"В открытом доступе доступно {open_access_count} из {len(papers)} источников.",
        ]
    return [
        f"The most influential paper in the set is '{highest_cited.title}'.",
        f"{open_access_count} out of {len(papers)} sources are available in open access.",
    ]


def _build_future_work(papers: list[Paper], language: SupportedLanguage) -> list[str]:
    newest_year = max((paper.year or 0) for paper in papers) if papers else 0
    if language == "ru":
        return [
            f"Стоит продолжить анализ свежих публикаций после {newest_year or 'последних доступных лет'} и проверить, как меняются данные и методики.",
            "Полезно дополнить корпус статьями с открытым полным текстом для более глубокого сравнения.",
        ]
    return [
        f"Future work should track papers published after {newest_year or 'the latest available year'} to capture newer datasets and methods.",
        "It would also help to expand the corpus with more full-text open-access papers for deeper comparison.",
    ]


def _papers_context(papers: list[Paper]) -> str:
    lines = []
    for paper in papers:
        lines.append(
            f"- {paper.title} | authors={', '.join(paper.authors) or 'n/a'} | "
            f"year={paper.year or 'n/a'} | source={paper.source} | citations={paper.citation_count}"
        )
    return "\n".join(lines) or "- no papers"
