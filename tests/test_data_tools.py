"""Tests for data tool helpers relying on market data adapters."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from autogentest1.tools import data_tools


def _history(values: Dict[str, float]) -> pd.DataFrame:
    dates = pd.to_datetime(list(values.keys()))
    return pd.DataFrame({"Close": list(values.values())}, index=dates)


def test_get_gold_silver_ratio_uses_primary_pair(monkeypatch) -> None:
    sequences: Dict[str, pd.DataFrame] = {
        "XAUUSD": _history({"2024-01-01": 2000.0, "2024-01-02": 2010.0}),
        "XAGUSD": _history({"2024-01-01": 25.0, "2024-01-02": 26.0}),
    }

    def fake_fetch(symbol: str, days: int = 60):  # pragma: no cover - deterministic
        return sequences.get(symbol, pd.DataFrame(columns=["Close"]))

    monkeypatch.setattr(data_tools, "fetch_price_history", fake_fetch)

    result = data_tools.get_gold_silver_ratio(days=60)

    assert result["pair"] == {"gold": "XAUUSD", "silver": "XAGUSD"}
    assert result["latest"] == 2010.0 / 26.0
    assert result["series"][-1]["ratio"] == result["latest"]


def test_get_gold_silver_ratio_falls_back(monkeypatch) -> None:
    empty = pd.DataFrame(columns=["Close"])
    sequences: Dict[str, pd.DataFrame] = {
        "XAUUSD": empty,
        "XAGUSD": empty,
        "GC=F": _history({"2024-01-01": 2050.0}),
        "SI=F": _history({"2024-01-01": 24.0}),
    }

    def fake_fetch(symbol: str, days: int = 60):  # pragma: no cover - deterministic
        return sequences.get(symbol, empty)

    monkeypatch.setattr(data_tools, "fetch_price_history", fake_fetch)

    result = data_tools.get_gold_silver_ratio(days=60)

    assert result["pair"] == {"gold": "GC=F", "silver": "SI=F"}
    assert result["latest"] == 2050.0 / 24.0


def test_get_macro_snapshot_uses_adapter(monkeypatch) -> None:
    sequences: Dict[str, pd.DataFrame] = {
        "DX-Y.NYB": _history({"2024-01-01": 104.0}),
        "TIP": _history({"2024-01-01": 108.5}),
    }

    def fake_fetch(symbol: str, days: int = 45):  # pragma: no cover - deterministic
        return sequences.get(symbol, pd.DataFrame(columns=["Close"]))

    monkeypatch.setattr(data_tools, "fetch_price_history", fake_fetch)

    result = data_tools.get_macro_snapshot()

    assert result["usd_index"]["symbol"] == "DX-Y.NYB"
    assert result["tips_etf"]["symbol"] == "TIP"
    assert result["usd_index"]["records"]
    assert result["tips_etf"]["records"]
