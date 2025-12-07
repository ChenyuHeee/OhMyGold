#!/usr/bin/env python3
"""Bootstrap script to ingest macro-history documents into the RAG index."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Iterable, List

from ohmygold.tools.rag import RagConfig, RagDocument, RagService


def _load_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Unsupported JSON payload: expected object in {path}")


def _discover_sources(sources: Iterable[Path]) -> List[Path]:
    paths: List[Path] = []
    for source in sources:
        if source.is_dir():
            for ext in ("*.json", "*.md", "*.txt"):
                paths.extend(sorted(source.glob(ext)))
        elif source.is_file():
            paths.append(source)
    return sorted({path.resolve() for path in paths})


def _iter_documents(paths: Iterable[Path]) -> Iterable[RagDocument]:
    for path in paths:
        suffix = path.suffix.lower()
        if suffix == ".json":
            try:
                payload = _load_json(path)
            except ValueError as exc:
                print(f"Skipping {path}: {exc}")
                continue
            body = str(payload.pop("body", "")).strip()
            if not body:
                continue
            metadata = {"source": str(path)}
            metadata.update(payload)
            yield RagDocument(body=body, metadata=metadata)
        else:
            body = _load_markdown(path)
            if not body:
                continue
            yield RagDocument(body=body, metadata={"source": str(path)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest macro/trading history into vector store")
    parser.add_argument(
        "sources",
        nargs="*",
        type=Path,
        help="Files or directories containing .md/.txt/.json documents",
    )
    parser.add_argument(
        "--index-root",
        type=Path,
        default=Path("data/rag-index"),
        help="Directory for persisted vector index",
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="gold-playbooks",
        help="Namespace (collection name) to ingest into",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=None,
        help="Optional tag to attach to document metadata (can be repeated)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("outputs/ingest_logs"),
        help="Directory for ingestion summary logs",
    )
    args = parser.parse_args()

    provided_sources = list(args.sources)
    default_corpora = [
        Path("data/rag/macro_history"),
        Path("data/rag/trading_playbook"),
    ]
    if not provided_sources:
        provided_sources = [path for path in default_corpora if path.exists()]

    source_paths = _discover_sources(provided_sources)
    if not source_paths:
        raise SystemExit("No source documents found. Provide --sources or place files under data/rag/macro_history.")

    config = RagConfig(
        index_root=args.index_root,
        namespace=args.namespace,
    )
    service = RagService(config)

    tags = [tag.strip() for tag in (args.tag or []) if tag and tag.strip()]

    def _tagged_documents() -> Iterable[RagDocument]:
        for document in _iter_documents(source_paths):
            if tags:
                metadata = dict(document.metadata)
                metadata.setdefault("tags", [])
                if isinstance(metadata["tags"], list):
                    metadata["tags"].extend(tags)
                else:
                    metadata["tags"] = tags
                yield RagDocument(body=document.body, metadata=metadata)
            else:
                yield document

    doc_iterable = _tagged_documents()
    count = service.ingest_documents(doc_iterable)
    print(f"Ingested {count} document(s) into namespace '{config.namespace}' at {config.index_root}")

    args.log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    summary = {
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "namespace": config.namespace,
        "index_root": str(config.index_root),
        "documents": count,
        "sources": [str(path) for path in source_paths],
        "tags": tags,
    }
    log_path = args.log_dir / f"ingest_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    log_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote ingest summary to {log_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
