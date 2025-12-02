"""Helpers for converting data structures to JSON-friendly formats."""

from __future__ import annotations

from importlib import import_module
from math import isnan
from typing import Any, Dict, Iterable, List

try:  # pragma: no cover - optional dependency resolution
    import_module("pandas")
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ImportError("The 'pandas' package is required for serialization helpers.") from exc


def df_to_records(frame: Any, *, include_index: bool = True) -> List[Dict[str, Any]]:
    """Convert a DataFrame to a list of JSON-serializable dict records."""

    if frame.empty:
        return []

    if include_index:
        frame = frame.copy()
        frame.reset_index(inplace=True)

    records = frame.to_dict(orient="records")

    def _convert(value: Any) -> Any:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if isinstance(value, (int, float)):
            numeric = float(value)
            return None if isnan(numeric) else numeric
        return value

    return [
        {key: _convert(value) for key, value in record.items()}
        for record in records
    ]


def to_key_value_pairs(items: Iterable[str], *, category: str) -> List[Dict[str, str]]:
    """Wrap plain strings into structured key/value documents."""

    return [{"category": category, "detail": text} for text in items]
