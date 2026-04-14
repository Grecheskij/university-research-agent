"""Formatting helpers for the Gradio frontend."""

from __future__ import annotations

from typing import Any

from frontend.i18n import Language, t


def split_identifiers(raw_value: str) -> tuple[list[str], list[str]]:
    """Split textarea input into DOI values and generic paper identifiers."""

    dois: list[str] = []
    paper_ids: list[str] = []
    for line in raw_value.splitlines():
        value = line.strip().strip(",;")
        if not value:
            continue
        if value.startswith("10.") and "/" in value:
            dois.append(value)
        else:
            paper_ids.append(value)
    return dois, paper_ids


def truncate_text(value: str | None, *, limit: int = 280) -> str:
    """Truncate long text for compact result cards."""

    if not value:
        return ""
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def format_papers_markdown(papers: list[dict[str, Any]], language: Language) -> str:
    """Render papers as readable Markdown cards."""

    if not papers:
        return t(language, "no_results")

    cards: list[str] = []
    for paper in papers:
        title = paper.get("title") or "Untitled"
        authors = ", ".join(paper.get("authors") or []) or "n/a"
        year = paper.get("year") or "n/a"
        source = paper.get("source") or "n/a"
        citations = paper.get("citation_count")
        abstract = truncate_text(paper.get("abstract"))
        url = paper.get("url")
        pdf_url = paper.get("pdf_url")
        links: list[str] = []
        if url:
            links.append(f"[URL]({url})")
        if pdf_url:
            links.append(f"[PDF]({pdf_url})")
        if paper.get("id", "").startswith("10.") and "/" in paper.get("id", ""):
            doi = paper["id"]
            links.append(f"[DOI](https://doi.org/{doi})")

        cards.append(
            "\n".join(
                [
                    f"### {title}",
                    f"**Authors:** {authors}",
                    f"**Year:** {year}  ",
                    f"**{t(language, 'summary_sources')}:** {source}  ",
                    f"**{t(language, 'summary_citations')}:** {citations if citations is not None else 'n/a'}",
                    abstract if abstract else "",
                    " | ".join(links) if links else "",
                ]
            ).strip()
        )
    return "\n\n---\n\n".join(cards)


def format_source_stats_markdown(source_stats: dict[str, int] | None, language: Language) -> str:
    """Render source statistics for search results."""

    if not source_stats:
        return t(language, "empty_state")
    lines = [f"- **{source}**: {count}" for source, count in sorted(source_stats.items())]
    return "\n".join(lines)


def format_bibliography_markdown(entries: list[str], language: Language) -> str:
    """Render bibliography entries as a copy-friendly list."""

    if not entries:
        return t(language, "no_results")
    return "\n".join(f"{index}. {entry}" for index, entry in enumerate(entries, start=1))


def format_analytics_markdown(
    source_distribution: dict[str, int],
    year_distribution: dict[str, int],
    citation_stats: dict[str, Any],
    language: Language,
) -> str:
    """Render analytics payload as Markdown."""

    if not source_distribution and not year_distribution:
        return t(language, "empty_state")

    source_lines = "\n".join(
        f"- **{source}**: {count}" for source, count in sorted(source_distribution.items())
    ) or "-"
    year_lines = "\n".join(
        f"- **{year}**: {count}" for year, count in sorted(year_distribution.items())
    ) or "-"
    citation_lines = "\n".join(
        [
            f"- **count**: {citation_stats.get('count')}",
            f"- **mean**: {citation_stats.get('mean')}",
            f"- **max**: {citation_stats.get('max')}",
        ]
    )
    return "\n\n".join(
        [
            f"### {t(language, 'summary_sources')}\n{source_lines}",
            f"### Years\n{year_lines}",
            f"### Citation stats\n{citation_lines}",
        ]
    )
