"""Tests for lightweight backtesting helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from ohmygold.services.backtest import run_backtest
from ohmygold.tools import backtest_tools


def _mock_history(values: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=len(values), freq="B")
    return pd.DataFrame({"Close": values}, index=dates)


def test_buy_and_hold_backtest_matches_price_return() -> None:
    history = _mock_history([100, 101, 102, 103, 104, 105])
    result = run_backtest(history, strategy="buy_and_hold", initial_capital=100_000.0)

    metrics = result["metrics"]
    assert pytest.approx(metrics["total_return"], rel=1e-6) == 0.05
    assert pytest.approx(result["equity_curve"][-1]["equity"], rel=1e-6) == 105_000.0
    assert result["trades"][0]["return_pct"] == pytest.approx(0.05)


def test_sma_crossover_generates_trades() -> None:
    values = [100, 99, 98, 99, 100, 102, 103, 101, 99, 100, 102, 104]
    history = _mock_history(values)
    params = {"short_window": 2, "long_window": 4}
    result = run_backtest(history, strategy="sma_crossover", initial_capital=50_000.0, params=params)

    trades = result["trades"]
    assert trades, "SMA crossover should create at least one trade"
    assert all(trade["entry_date"] <= trade["exit_date"] for trade in trades)


def test_backtest_tool_handles_missing_data(monkeypatch) -> None:
    def fake_fetch(symbol: str, days: int):
        return pd.DataFrame({"Close": []})

    monkeypatch.setattr(backtest_tools, "fetch_price_history", fake_fetch)

    output = backtest_tools.run_backtest(symbol="TEST", days=30)
    assert "error" in output
    assert output["symbol"] == "TEST"

