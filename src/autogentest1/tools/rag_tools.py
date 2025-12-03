"""RAG helper utilities exposed through the AutoGen ToolsProxy."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..config.settings import Settings, get_settings
from .rag.client import RagConfig, RagDocument, RagQueryResult, RagService

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SUPPORTED_SUFFIXES = {".json", ".md", ".txt"}


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        return (_PROJECT_ROOT / path).resolve()
    return path.resolve()


def _sanitise_settings(settings: Settings) -> tuple[str, str, int, int, float]:
    chunk_size = max(32, int(settings.rag_chunk_size))
    overlap = max(0, min(int(settings.rag_chunk_overlap), chunk_size - 1))
    threshold = max(0.0, min(1.0, float(settings.rag_similarity_threshold)))
    index_root = str(_resolve_path(settings.rag_index_root))
    namespace = settings.rag_namespace or "default"
    return index_root, namespace, chunk_size, overlap, threshold


@lru_cache(maxsize=8)
def _build_service(
    index_root: str,
    namespace: str,
    chunk_size: int,
    overlap: int,
    similarity_threshold: float,
) -> RagService:
    config = RagConfig(
        index_root=Path(index_root),
        namespace=namespace,
        chunk_size=chunk_size,
        overlap=overlap,
        similarity_threshold=similarity_threshold,
    )
    return RagService(config)


def _get_service(settings: Optional[Settings] = None, namespace: Optional[str] = None) -> RagService:
    loaded_settings = settings or get_settings()
    index_root, default_namespace, chunk_size, overlap, threshold = _sanitise_settings(loaded_settings)
    effective_namespace = namespace or default_namespace
    return _build_service(index_root, effective_namespace, chunk_size, overlap, threshold)


def reset_rag_cache() -> None:
    """Clear cached service instances (useful for tests)."""

    _build_service.cache_clear()


def _document_from_json(path: Path) -> Optional[RagDocument]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    body = str(payload.pop("body", "")).strip()
    if not body:
        return None
    metadata = {key: value for key, value in payload.items() if value is not None}
    metadata["source"] = str(path)
    return RagDocument(body=body, metadata=metadata)


def _document_from_text(path: Path) -> Optional[RagDocument]:
    try:
        body = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not body:
        return None
    metadata = {"source": str(path), "format": path.suffix.lower().lstrip(".")}
    return RagDocument(body=body, metadata=metadata)


def _iter_corpus_documents(paths: Iterable[str]) -> Sequence[RagDocument]:
    documents: List[RagDocument] = []
    for root_str in paths:
        root_path = _resolve_path(root_str)
        if not root_path.exists():
            continue
        for file_path in root_path.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
                continue
            if file_path.suffix.lower() == ".json":
                document = _document_from_json(file_path)
            else:
                document = _document_from_text(file_path)
            if document is not None:
                documents.append(document)
    return documents


def ensure_default_corpus_loaded(
    *,
    force: bool = False,
    namespace: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Ingest the configured RAG corpus into the persistent index.

    Parameters
    ----------
    force:
        When ``True`` all eligible files are re-ingested even if they already appear in the index.
    namespace:
        Override the namespace defined in settings.
    settings:
        Inject a settings object (mainly for testing).
    """

    loaded_settings = settings or get_settings()
    service = _get_service(loaded_settings, namespace)
    corpus_paths = loaded_settings.rag_corpus_paths or []
    documents = _iter_corpus_documents(corpus_paths)
    if not documents:
        return {"documents": 0, "chunks": 0, "skipped": 0}

    existing_sources = set() if force else set(service.list_sources())
    to_index: List[RagDocument] = []
    for document in documents:
        source = document.metadata.get("source")
        if isinstance(source, str) and source in existing_sources and not force:
            continue
        to_index.append(document)

    if not to_index:
        return {
            "documents": 0,
            "chunks": 0,
            "skipped": len(documents),
        }

    chunk_count = service.ingest_documents(to_index)
    return {
        "documents": len(to_index),
        "chunks": chunk_count,
        "skipped": len(documents) - len(to_index),
    }


def ingest_documents(
    documents: Sequence[Mapping[str, Any]],
    *,
    namespace: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Ingest arbitrary documents through the ToolsProxy interface."""

    if not documents:
        return {"documents": 0, "chunks": 0}

    rag_documents: List[RagDocument] = []
    for item in documents:
        if not isinstance(item, Mapping):
            continue
        body = str(item.get("body", "")).strip()
        if not body:
            continue
        metadata = {
            key: value for key, value in item.items() if key != "body" and value is not None
        }
        metadata.setdefault("source", item.get("source", "tools_proxy"))
        rag_documents.append(RagDocument(body=body, metadata=metadata))

    if not rag_documents:
        return {"documents": 0, "chunks": 0}

    service = _get_service(settings, namespace)
    chunk_count = service.ingest_documents(rag_documents)
    return {"documents": len(rag_documents), "chunks": chunk_count}


def query_playbook(
    question: str,
    *,
    top_k: int = 5,
    namespace: Optional[str] = None,
    ensure_corpus: bool = True,
    settings: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Query the configured RAG index for contextual playbooks and precedents."""

    loaded_settings = settings or get_settings()
    service = _get_service(loaded_settings, namespace)
    if ensure_corpus and loaded_settings.rag_auto_ingest:
        ensure_default_corpus_loaded(namespace=namespace, settings=loaded_settings)

    result: RagQueryResult = service.query(question, top_k=top_k)
    return {
        "question": result.question,
        "passages": result.passages,
        "scores": result.scores,
        "metadata": result.metadata,
        "ids": result.ids,
    }


__all__ = [
    "ensure_default_corpus_loaded",
    "ingest_documents",
    "query_playbook",
    "reset_rag_cache",
]
