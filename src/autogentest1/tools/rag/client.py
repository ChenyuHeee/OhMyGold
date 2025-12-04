"""RAG client backed by a persistent Chroma vector store."""

from __future__ import annotations

import math
import re
import uuid
import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:  # pragma: no cover - dependency resolution happens at runtime
    import chromadb  # type: ignore
except Exception as _exc:  # pragma: no cover - exercised when chromadb missing
    chromadb = None  # type: ignore
    _CHROMADB_IMPORT_ERROR = _exc
else:  # pragma: no cover - keep reference for debugging
    _CHROMADB_IMPORT_ERROR = None


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    """Lower-case word tokenisation compatible with ascii-only corpora."""

    return _TOKEN_PATTERN.findall(text.lower())

class HashingEmbeddingFunction:
    """Deterministic hashing-based embedding function compatible with Chroma."""

    def __init__(self, *, dimensions: int = 1024) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def __call__(self, input: Sequence[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in input:
            counts = [0.0] * self.dimensions
            for token in _tokenize(text):
                digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
                bucket = int(digest, 16) % self.dimensions
                counts[bucket] += 1.0
            norm = math.sqrt(sum(value * value for value in counts))
            if norm > 0.0:
                counts = [value / norm for value in counts]
            vectors.append(counts)
        return vectors

    def name(self) -> str:
        """Return the identifier expected by newer Chroma releases."""

        return "autogentest1-hashing"

    def embed_documents(self, input: Sequence[str]) -> List[List[float]]:  # pragma: no cover - thin wrapper
        return self(input)

    def embed_query(self, input: Sequence[str]) -> List[List[float]]:  # pragma: no cover - thin wrapper
        return self(input)


@dataclass
class RagConfig:
    """RAG service configuration and file-system integration hints."""

    index_root: Path
    namespace: str = "default"
    embedding_dimensions: int = 1024
    chunk_size: int = 200
    overlap: int = 25
    distance_metric: str = "cosine"
    similarity_threshold: float = 0.1

    def ensure_directories(self) -> None:
        """Create index directories so ingestion scripts can write artifacts."""

        self.index_root.mkdir(parents=True, exist_ok=True)


@dataclass
class RagDocument:
    """Structured input payload for ingestion."""

    body: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _StoredChunk:
    """Internal representation used during ingestion."""

    chunk_id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class RagQueryResult:
    """Structured payload returned from the RAG service."""

    question: str
    passages: List[str] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    metadata: List[dict] = field(default_factory=list)
    ids: List[str] = field(default_factory=list)

    def top_passage(self) -> Optional[str]:
        """Convenience accessor for the highest-ranked passage."""

        return self.passages[0] if self.passages else None


class RagService:
    """Interface to a persistent Chroma collection."""

    def __init__(self, config: RagConfig) -> None:
        if chromadb is None:  # pragma: no cover - triggered in envs without chromadb
            message = (
                "chromadb is not available. Install a version compatible with Pydantic 2.x "
                "(e.g. 'pip install \"chromadb>=0.5\"') to enable RAG features."
            )
            raise RuntimeError(message) from _CHROMADB_IMPORT_ERROR
        self.config = config
        self.config.ensure_directories()
        self._embedding_function = HashingEmbeddingFunction(dimensions=self.config.embedding_dimensions)
        self._client = chromadb.PersistentClient(path=str(self.config.index_root))  # type: ignore[attr-defined]
        self._collection = self._client.get_or_create_collection(
            name=self.config.namespace,
            metadata={"hnsw:space": self.config.distance_metric},
            embedding_function=self._embedding_function,
        )

    # ------------------------------------------------------------------
    # Ingestion & querying
    # ------------------------------------------------------------------
    def ingest_documents(self, documents: Iterable[Any]) -> int:
        """Ingest documents into the vector store and return the chunk count."""

        prepared: List[_StoredChunk] = []
        for raw in documents:
            document = self._coerce_document(raw)
            if document is None:
                continue
            chunks = self._chunk_text(document.body)
            if not chunks:
                continue
            total_chunks = len(chunks)
            for idx, text in enumerate(chunks):
                metadata = dict(document.metadata)
                metadata.setdefault("source", metadata.get("source", "unknown"))
                metadata.update({
                    "chunk_index": idx,
                    "chunk_count": total_chunks,
                })
                prepared.append(
                    _StoredChunk(
                        chunk_id=str(uuid.uuid4()),
                        text=text,
                        metadata=metadata,
                    )
                )

        if not prepared:
            return 0

        self._collection.add(
            ids=[chunk.chunk_id for chunk in prepared],
            documents=[chunk.text for chunk in prepared],
            metadatas=[chunk.metadata for chunk in prepared],
        )
        return len(prepared)

    def _coerce_document(self, raw: Any) -> Optional[RagDocument]:
        if raw is None:
            return None
        if isinstance(raw, RagDocument):
            return raw
        if isinstance(raw, Path):
            text = raw.read_text(encoding="utf-8").strip()
            if not text:
                return None
            return RagDocument(body=text, metadata={"source": str(raw)})
        if isinstance(raw, dict):
            body = str(raw.get("body", ""))
            if not body.strip():
                return None
            metadata = {key: value for key, value in raw.items() if key != "body"}
            return RagDocument(body=body, metadata=metadata)
        if isinstance(raw, str):
            cleaned = raw.strip()
            if not cleaned:
                return None
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    return self._coerce_document(parsed)
            except json.JSONDecodeError:
                pass
            return RagDocument(body=cleaned, metadata={"source": "raw_text"})
        return None

    def _chunk_text(self, text: str) -> List[str]:
        words = text.split()
        if not words:
            return []
        chunk_size = max(1, self.config.chunk_size)
        overlap = max(0, min(self.config.overlap, chunk_size - 1))
        step = max(1, chunk_size - overlap)
        chunks: List[str] = []
        for start in range(0, len(words), step):
            slice_words = words[start : start + chunk_size]
            if not slice_words:
                continue
            chunks.append(" ".join(slice_words))
        return chunks or [" ".join(words)]

    def query(self, question: str, *, top_k: int = 5) -> RagQueryResult:
        """Return the closest matching passages for the supplied question."""

        if self.count() == 0:
            return RagQueryResult(question=question)

        limit = max(1, min(top_k, 50))
        result = self._collection.query(
            query_texts=[question],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]

        passages: List[str] = []
        scores: List[float] = []
        metadata: List[Dict[str, Any]] = []
        chunk_ids: List[str] = []
        threshold = max(0.0, float(self.config.similarity_threshold))
        for index, doc in enumerate(documents):
            if not isinstance(doc, str):
                continue
            meta = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            chunk_id = ids[index] if index < len(ids) else None
            if isinstance(distance, (int, float)):
                similarity = max(0.0, 1.0 - float(distance))
            else:
                similarity = 0.0
            if similarity < threshold:
                continue
            passages.append(doc)
            scores.append(similarity)
            metadata.append(dict(meta) if isinstance(meta, dict) else {})
            chunk_ids.append(str(chunk_id) if chunk_id is not None else "")

        return RagQueryResult(
            question=question,
            passages=passages,
            scores=scores,
            metadata=metadata,
            ids=chunk_ids,
        )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def count(self) -> int:
        """Return the number of stored chunks (useful for diagnostics)."""

        return int(self._collection.count())

    def list_sources(self) -> List[str]:
        """Return unique sources present in the current namespace."""

        raw = self._collection.get(include=["metadatas"], limit=5000)
        entries = raw.get("metadatas") or []
        if entries and isinstance(entries[0], list):
            metadata_entries = entries[0]
        else:
            metadata_entries = entries
        sources = set()
        for entry in metadata_entries:
            if isinstance(entry, dict):
                source = entry.get("source")
                if source:
                    sources.add(str(source))
        return sorted(sources)
