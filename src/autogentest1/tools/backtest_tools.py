"""Backtest helpers exposed through the AutoGen ToolsProxy."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..services.backtest import run_backtest as _run_backtest
from ..services.market_data import fetch_price_history


def run_backtest(
    *,
    symbol: str = "XAUUSD",
    days: int = 365,
    strategy: str = "buy_and_hold",
    initial_capital: float = 1_000_000.0,
    params: Optional[Dict[str, Any]] = None,
    risk_free_rate: float = 0.0,
) -> Dict[str, Any]:
    """Fetch price history and execute a named backtest strategy.

    Parameters
    ----------
    symbol:
        Market ticker to evaluate (defaults to spot gold XAUUSD).
    days:
        Number of trailing calendar days to request via the configured data provider.
    strategy:
        One of 'buy_and_hold', 'sma_crossover', or 'mean_reversion'.
    initial_capital:
        Starting capital for the simulation (USD).
    params:
        Optional strategy-specific parameters (e.g., short_window / long_window for SMA).
    risk_free_rate:
        Annualized risk-free rate used in the Sharpe ratio calculation.
    """

    history = fetch_price_history(symbol, days=days)
    if history.empty:
        return {
            "error": f"No historical data returned for {symbol} ({days}d).",
            "symbol": symbol,
            "days": days,
            "strategy": strategy,
        }

    safe_params = dict(params or {})
    safe_params.setdefault("symbol", symbol)

    try:
        return _run_backtest(
            history,
            strategy=strategy,
            initial_capital=initial_capital,
            params=safe_params,
            risk_free_rate=risk_free_rate,
        )
    except ValueError as exc:
        return {
            "error": str(exc),
            "symbol": symbol,
            "days": days,
            "strategy": strategy,
        }

