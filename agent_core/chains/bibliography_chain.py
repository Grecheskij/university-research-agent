"""Bibliography formatting chain implementation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_core.language import SupportedLanguage
from data.schemas.paper_schema import Paper


class BibliographyResult(BaseModel):
    """Formatted bibliography in three citation styles."""

    language: SupportedLanguage
    apa: list[str] = Field(default_factory=list)
    mla: list[str] = Field(default_factory=list)
    gost: list[str] = Field(default_factory=list)


class BibliographyChain:
    """Generate APA, MLA, and GOST bibliography entries."""

    def __init__(self, *, llm: Any | None = None) -> None:
        self.llm = llm

    async def run(
        self,
        papers: list[Paper],
        *,
        language: SupportedLanguage = "ru",
    ) -> BibliographyResult:
        """Format all papers into APA 7, MLA 9, and GOST 7.0.5 entries."""

        unique_papers = _merge_papers(papers)
        return BibliographyResult(
            language=language,
            apa=[_format_apa(paper) for paper in unique_papers],
            mla=[_format_mla(paper) for paper in unique_papers],
            gost=[_format_gost(paper) for paper in unique_papers],
        )


def _merge_papers(papers: list[Paper]) -> list[Paper]:
    unique: dict[tuple[str, str], Paper] = {}
    for paper in papers:
        unique[(paper.source, paper.id)] = paper
    return list(unique.values())


def _format_apa(paper: Paper) -> str:
    author_text = _format_authors_apa(paper.authors)
    year_text = f"({paper.year})." if paper.year else "(n.d.)."
    locator = _locator_text(paper)
    return f"{author_text} {year_text} {paper.title}. {locator}".strip()


def _format_mla(paper: Paper) -> str:
    author_text = _format_authors_mla(paper.authors)
    year_text = str(paper.year) if paper.year else "n.d."
    locator = _locator_text(paper)
    return f"{author_text} \"{paper.title}.\" {paper.source.title()}, {year_text}, {locator}".strip()


def _format_gost(paper: Paper) -> str:
    author_text = _format_authors_gost(paper.authors)
    year_text = str(paper.year) if paper.year else "б. г."
    locator = _locator_text(paper)
    return f"{author_text} {paper.title} // {paper.source}. {year_text}. {locator}".strip()


def _format_authors_apa(authors: list[str]) -> str:
    if not authors:
        return ""
    formatted = [_surname_and_initials(author) for author in authors[:3]]
    return ", ".join(formatted) + "."


def _format_authors_mla(authors: list[str]) -> str:
    if not authors:
        return ""
    if len(authors) == 1:
        surname, given = _split_name(authors[0])
        return f"{surname}, {given}."
    if len(authors) == 2:
        first_surname, first_given = _split_name(authors[0])
        return f"{first_surname}, {first_given}, and {authors[1]}."
    first_surname, first_given = _split_name(authors[0])
    return f"{first_surname}, {first_given}, et al."


def _format_authors_gost(authors: list[str]) -> str:
    if not authors:
        return ""
    formatted = [_gost_name(author) for author in authors[:3]]
    return ", ".join(formatted) + "."


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in full_name.split() if part]
    if not parts:
        return "Unknown", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def _surname_and_initials(full_name: str) -> str:
    surname, given_names = _split_name(full_name)
    initials = " ".join(f"{part[0]}." for part in given_names.split() if part)
    return f"{surname}, {initials}".strip().replace("  ", " ")


def _gost_name(full_name: str) -> str:
    surname, given_names = _split_name(full_name)
    initials = " ".join(f"{part[0]}." for part in given_names.split() if part)
    return f"{surname} {initials}".strip()


def _locator_text(paper: Paper) -> str:
    if paper.url:
        return paper.url
    if paper.id.startswith("10.") and "/" in paper.id:
        return f"DOI: {paper.id}"
    return paper.id
