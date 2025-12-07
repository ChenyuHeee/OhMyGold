"""Tests for quantitative helper utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pathlib import Path

from ohmygold.tools import quant_helpers


def _make_history(values: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({
        "Open": values,
        "High": values + 2.0,
        "Low": values - 2.0,
        "Close": values,
        "Adj Close": values,
        "Volume": np.full(len(values), 100_000),
    })
    frame.index = values.index
    return frame


def test_prepare_quant_dataset_returns_summary(monkeypatch) -> None:
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    base_prices = pd.Series(np.linspace(1900.0, 1959.0, len(dates)), index=dates)
    history = _make_history(base_prices)

    monkeypatch.setattr(quant_helpers, "fetch_price_history", lambda symbol, days=365: history)

    payload = quant_helpers.prepare_quant_dataset(symbol="XAUUSD", days=60)

    assert payload["summary"]["last_close"] == pytest.approx(float(base_prices.iloc[-1]))
    assert payload["summary"]["volatility_20d"] is not None
    assert payload["records"], "Expected non-empty records for downstream charting"


def test_prepare_quant_dataset_handles_no_data(monkeypatch) -> None:
    monkeypatch.setattr(quant_helpers, "fetch_price_history", lambda symbol, days=365: pd.DataFrame())
    payload = quant_helpers.prepare_quant_dataset(symbol="XAUUSD", days=30)
    assert "error" in payload
    assert payload["records"] == []


def test_compute_factor_exposures_returns_metrics(monkeypatch) -> None:
    dates = pd.date_range("2024-02-01", periods=40, freq="B")
    base_prices = pd.Series(np.linspace(1900.0, 1940.0, len(dates)), index=dates)
    factor_a = base_prices * 0.5 + 10
    factor_b = base_prices * -0.3 + 5

    def fake_fetch(symbol: str, days: int = 365):
        if symbol == "XAUUSD":
            return _make_history(base_prices)
        if symbol == "FACTOR_A":
            return _make_history(pd.Series(factor_a.values, index=dates))
        if symbol == "FACTOR_B":
            return _make_history(pd.Series(factor_b.values, index=dates))
        return pd.DataFrame()

    monkeypatch.setattr(quant_helpers, "fetch_price_history", fake_fetch)

    exposures = quant_helpers.compute_factor_exposures(
        symbol="XAUUSD",
        benchmarks=("FACTOR_A", "FACTOR_B"),
        days=40,
    )

    assert exposures["benchmarks"], "Expected exposures for provided factors"
    seen_symbols = {entry.get("symbol") for entry in exposures["benchmarks"]}
    assert {"FACTOR_A", "FACTOR_B"}.issubset(seen_symbols)
    for entry in exposures["benchmarks"]:
        if entry.get("status") is None:
            assert entry["observations"] > 0
            assert entry["correlation"] is not None
            assert entry["beta"] is not None


def test_generate_volatility_cone_chart_creates_file(monkeypatch, tmp_path) -> None:
    dates = pd.date_range("2024-01-01", periods=120, freq="B")
    prices = pd.Series(np.linspace(1800.0, 1880.0, len(dates)) + np.sin(np.linspace(0, 6, len(dates))) * 15, index=dates)
    history = _make_history(prices)

    monkeypatch.setattr(quant_helpers, "fetch_price_history", lambda symbol, days=365: history)

    result = quant_helpers.generate_volatility_cone_chart(
        symbol="XAUUSD",
        days=120,
        windows=(5, 10, 20),
        output_dir=tmp_path,
    )

    assert "chart_path" in result
    assert Path(result["chart_path"]).exists()
    assert result["metrics"]


def test_generate_volatility_cone_chart_handles_empty(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(quant_helpers, "fetch_price_history", lambda *_, **__: pd.DataFrame())

    result = quant_helpers.generate_volatility_cone_chart(
        symbol="XAUUSD",
        days=30,
        output_dir=tmp_path,
    )

    assert "error" in result
