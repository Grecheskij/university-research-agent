"""Chroma-backed vector store manager for research papers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
import logging
import math
import re

from agent_core.config import CoreSettings, get_settings
from data.schemas.paper_schema import Paper

LOGGER = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:  # pragma: no cover - optional dependency
    chromadb = None
    SentenceTransformerEmbeddingFunction = None

_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class InMemoryPaperCollection:
    """Small fallback collection used when Chroma is unavailable."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def add(self, *, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]) -> None:
        """Store documents and metadata by identifier."""

        for identifier, document, metadata in zip(ids, documents, metadatas, strict=False):
            self._records[identifier] = {"document": document, "metadata": metadata}

    def get(self, *, ids: list[str] | None = None) -> dict[str, list[Any]]:
        """Return stored documents for the requested ids."""

        selected_ids = ids or list(self._records)
        metadatas: list[dict[str, Any]] = []
        documents: list[str] = []
        resolved_ids: list[str] = []
        for identifier in selected_ids:
            record = self._records.get(identifier)
            if record is None:
                continue
            resolved_ids.append(identifier)
            metadatas.append(record["metadata"])
            documents.append(record["document"])
        return {"ids": resolved_ids, "metadatas": metadatas, "documents": documents}

    def query(self, *, query_texts: list[str], n_results: int) -> dict[str, list[list[Any]]]:
        """Return the closest in-memory matches for the query."""

        query = query_texts[0] if query_texts else ""
        ranked = sorted(
            self._records.values(),
            key=lambda record: _similarity_score(query, record["document"]),
            reverse=True,
        )[:n_results]
        return {
            "metadatas": [[record["metadata"] for record in ranked]],
            "documents": [[record["document"] for record in ranked]],
        }

    def delete(self) -> None:
        """Clear the in-memory collection."""

        self._records.clear()


class ChromaManager:
    """Manage paper indexing and retrieval against a Chroma collection."""

    def __init__(
        self,
        *,
        settings: CoreSettings | None = None,
        client: Any | None = None,
        collection: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client
        self._collection = collection

    @property
    def collection(self) -> Any:
        """Return the active vector collection."""

        if self._collection is None:
            self._collection = self._create_collection()
        return self._collection

    def add_papers(self, papers: Iterable[Paper]) -> list[str]:
        """Add deduplicated papers to the vector store and return stored ids."""

        normalized_papers = list(papers)
        if not normalized_papers:
            return []

        unique_papers: dict[str, Paper] = {}
        for paper in normalized_papers:
            unique_papers[self._paper_key(paper)] = paper

        candidate_ids = list(unique_papers)
        existing = self.collection.get(ids=candidate_ids)
        existing_ids = set(existing.get("ids", []))
        papers_to_store = {
            identifier: paper
            for identifier, paper in unique_papers.items()
            if identifier not in existing_ids
        }
        if not papers_to_store:
            return []

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for identifier, paper in papers_to_store.items():
            ids.append(identifier)
            documents.append(self._paper_document(paper))
            metadatas.append(self._paper_metadata(paper))

        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return ids

    def search(self, query: str, *, limit: int = 5) -> list[Paper]:
        """Query the vector store for relevant papers."""

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
        )
        metadatas = results.get("metadatas", [[]])
        if not metadatas or not metadatas[0]:
            return []
        return [self._paper_from_metadata(metadata) for metadata in metadatas[0]]

    def reset_collection(self) -> None:
        """Clear all indexed papers from the current collection."""

        if chromadb is not None and self._client is not None:
            self._client.delete_collection(self.settings.chroma_collection_name)
            self._collection = self._create_collection()
            return

        self.collection.delete()

    def _create_collection(self) -> Any:
        """Create or retrieve the configured vector collection."""

        if self._collection is not None:
            return self._collection

        if chromadb is None or SentenceTransformerEmbeddingFunction is None:
            LOGGER.warning("ChromaDB is unavailable; using in-memory vector store fallback.")
            return InMemoryPaperCollection()

        runtime_path = Path(self.settings.chroma_path)
        runtime_path.mkdir(parents=True, exist_ok=True)
        self._client = self._client or chromadb.PersistentClient(path=str(runtime_path))
        embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=self.settings.sentence_transformer_model
        )
        return self._client.get_or_create_collection(
            name=self.settings.chroma_collection_name,
            embedding_function=embedding_function,
        )

    def _paper_key(self, paper: Paper) -> str:
        """Return the deduplication key for a paper."""

        if _DOI_RE.match(paper.id):
            return f"doi:{paper.id.lower()}"
        return f"{paper.source}:{paper.id}"

    def _paper_document(self, paper: Paper) -> str:
        """Serialize a paper into searchable text."""

        parts = [paper.title]
        if paper.abstract:
            parts.append(paper.abstract)
        if paper.authors:
            parts.append(", ".join(paper.authors))
        if paper.year is not None:
            parts.append(str(paper.year))
        return "\n\n".join(parts)

    def _paper_metadata(self, paper: Paper) -> dict[str, Any]:
        """Serialize paper metadata for Chroma storage."""

        return {
            "paper_id": paper.id,
            "title": paper.title,
            "authors": " | ".join(paper.authors),
            "year": paper.year,
            "abstract": paper.abstract,
            "citation_count": paper.citation_count,
            "source": paper.source,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "open_access": paper.open_access,
        }

    def _paper_from_metadata(self, metadata: dict[str, Any]) -> Paper:
        """Reconstruct a paper from vector-store metadata."""

        authors_field = metadata.get("authors", "")
        authors = [author.strip() for author in authors_field.split(" | ") if author.strip()]
        return Paper(
            id=metadata["paper_id"],
            title=metadata["title"],
            authors=authors,
            year=metadata.get("year"),
            abstract=metadata.get("abstract"),
            citation_count=metadata.get("citation_count"),
            source=metadata["source"],
            url=metadata.get("url"),
            pdf_url=metadata.get("pdf_url"),
            open_access=metadata.get("open_access"),
        )


def _tokenize(text: str) -> set[str]:
    """Tokenize free text into lowercase terms for the fallback search mode."""

    return {token.lower() for token in _TOKEN_RE.findall(text)}


def _similarity_score(query: str, document: str) -> float:
    """Compute a simple overlap score for the in-memory fallback store."""

    query_tokens = _tokenize(query)
    document_tokens = _tokenize(document)
    if not query_tokens or not document_tokens:
        return 0.0
    intersection = len(query_tokens & document_tokens)
    return intersection / math.sqrt(len(query_tokens) * len(document_tokens))
