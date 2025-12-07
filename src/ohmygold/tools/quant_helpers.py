"""Quantitative analysis helpers for ToolsProxy workflows."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from ..services.indicators import compute_indicators
from ..services.market_data import fetch_price_history
from ..utils.plotting import plot_volatility_cone

# Default factors capture dollar, equity, and rates sensitivity.
DEFAULT_FACTOR_SYMBOLS: Sequence[str] = ("DX-Y.NYB", "^GSPC", "TLT")
_RECORD_LIMIT = 180


def _to_datetime_frame(history: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with a clean DatetimeIndex for downstream math."""

    if history.empty:
        return history
    frame = history.copy()
    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index)
    return frame.sort_index()


def _safe_tail_value(series: pd.Series) -> Optional[float]:
    if series is None or series.empty:
        return None
    value = float(series.iloc[-1])
    if math.isnan(value):
        return None
    return value


def _format_records(dataset: pd.DataFrame, columns: Sequence[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    tail = dataset.tail(_RECORD_LIMIT)
    for timestamp, row in tail.iterrows():
        if isinstance(timestamp, pd.Timestamp):
            ts = timestamp
        else:
            ts = pd.Timestamp(str(timestamp))
        entry: Dict[str, Any] = {"date": ts.strftime("%Y-%m-%d")}
        for column in columns:
            if column not in row:
                continue
            value = row[column]
            if isinstance(value, (float, int)):
                if not math.isnan(value):
                    entry[column] = float(value)
            elif pd.notna(value):
                entry[column] = value
        records.append(entry)
    return records


def prepare_quant_dataset(
    *,
    symbol: str = "XAUUSD",
    days: int = 365,
    fast_window: int = 20,
    slow_window: int = 50,
) -> Dict[str, Any]:
    """Return a structured payload of indicators ready for LLM consumption."""

    history = fetch_price_history(symbol, days=days)
    if history.empty:
        return {
            "symbol": symbol,
            "error": f"No historical data returned for {symbol} ({days} days lookback).",
            "records": [],
        }

    frame = _to_datetime_frame(history)
    close = frame["Close"].astype(float)
    returns = close.pct_change()

    dataset = pd.DataFrame({"close": close})
    dataset["return_1d"] = returns
    dataset["return_5d"] = close.pct_change(5)
    dataset["return_20d"] = close.pct_change(20)
    dataset["vol_20d"] = returns.rolling(window=20).std() * math.sqrt(252)
    dataset["drawdown"] = close / close.cummax() - 1.0

    rolling_mean = returns.rolling(window=20).mean()
    rolling_vol = returns.rolling(window=20).std()
    sharpe = (rolling_mean / rolling_vol) * math.sqrt(252)
    dataset["rolling_sharpe"] = sharpe.replace([np.inf, -np.inf], np.nan)

    indicators = compute_indicators(frame)
    if indicators:
        for key, series in indicators.items():
            dataset[key] = series

    dataset[f"sma_{fast_window}"] = close.rolling(window=fast_window, min_periods=fast_window // 2).mean()
    dataset[f"sma_{slow_window}"] = close.rolling(window=slow_window, min_periods=slow_window // 2).mean()
    dataset[f"ema_{fast_window}"] = close.ewm(span=max(2, fast_window), adjust=False).mean()
    dataset[f"ema_{slow_window}"] = close.ewm(span=max(2, slow_window), adjust=False).mean()

    last_idx = dataset.index[-1]
    summary = {
        "symbol": symbol,
        "lookback_days": days,
        "start": dataset.index[0].strftime("%Y-%m-%d"),
        "end": last_idx.strftime("%Y-%m-%d"),
        "last_close": float(close.iloc[-1]),
        "change_pct_1d": _safe_tail_value(dataset["return_1d"]),
        "change_pct_5d": _safe_tail_value(dataset["return_5d"]),
        "change_pct_20d": _safe_tail_value(dataset["return_20d"]),
        "volatility_20d": _safe_tail_value(dataset["vol_20d"]),
        "drawdown_pct": _safe_tail_value(dataset["drawdown"]),
        "rolling_sharpe": _safe_tail_value(dataset["rolling_sharpe"]),
        "rsi_14": _safe_tail_value(dataset.get("rsi_14", pd.Series(dtype=float))),
        "atr_14": _safe_tail_value(dataset.get("atr_14", pd.Series(dtype=float))),
        "sma_fast": _safe_tail_value(dataset[f"sma_{fast_window}"]),
        "sma_slow": _safe_tail_value(dataset[f"sma_{slow_window}"]),
        "ema_fast": _safe_tail_value(dataset[f"ema_{fast_window}"]),
        "ema_slow": _safe_tail_value(dataset[f"ema_{slow_window}"]),
    }

    records = _format_records(
        dataset,
        [
            "close",
            "return_1d",
            "return_5d",
            "return_20d",
            "vol_20d",
            "drawdown",
            "rolling_sharpe",
            "sma_20",
            "sma_50",
            "rsi_14",
            "atr_14",
            f"sma_{fast_window}",
            f"sma_{slow_window}",
            f"ema_{fast_window}",
            f"ema_{slow_window}",
        ],
    )

    return {
        "symbol": symbol,
        "summary": summary,
        "records": records,
    }


def compute_factor_exposures(
    *,
    symbol: str = "XAUUSD",
    benchmarks: Optional[Sequence[str]] = None,
    days: int = 365,
) -> Dict[str, Any]:
    """Estimate simple correlation/beta tilts versus common macro factors."""

    base_history = fetch_price_history(symbol, days=days)
    if base_history.empty:
        return {
            "symbol": symbol,
            "error": f"No historical data returned for {symbol} ({days} days lookback).",
            "benchmarks": [],
        }

    base = _to_datetime_frame(base_history)["Close"].astype(float).pct_change()
    factors = benchmarks or DEFAULT_FACTOR_SYMBOLS
    exposures: List[Dict[str, Any]] = []

    for factor_symbol in factors:
        ref_history = fetch_price_history(factor_symbol, days=days)
        if ref_history.empty:
            exposures.append({"symbol": factor_symbol, "status": "missing"})
            continue

        aligned = pd.DataFrame(
            {
                "asset": base,
                "factor": _to_datetime_frame(ref_history)["Close"].astype(float).pct_change(),
            }
        ).dropna()

        if aligned.empty:
            exposures.append({"symbol": factor_symbol, "status": "insufficient"})
            continue

        asset_vals = aligned["asset"].to_numpy(dtype=float)
        factor_vals = aligned["factor"].to_numpy(dtype=float)
        variance = float(np.var(factor_vals, ddof=1))
        if variance == 0.0 or math.isnan(variance):
            exposures.append({"symbol": factor_symbol, "status": "insufficient"})
            continue

        correlation_matrix = np.corrcoef(asset_vals, factor_vals)
        correlation = float(correlation_matrix[0, 1]) if correlation_matrix.size >= 4 else 0.0
        covariance = float(np.cov(asset_vals, factor_vals, ddof=1)[0, 1])
        beta = covariance / variance if variance else 0.0
        if math.isnan(correlation):
            correlation = 0.0
        if math.isnan(beta):
            beta = 0.0
        exposures.append(
            {
                "symbol": factor_symbol,
                "observations": int(len(aligned)),
                "correlation": correlation,
                "beta": beta,
            }
        )

    exposures.sort(key=lambda item: item.get("observations", 0), reverse=True)

    return {
        "symbol": symbol,
        "lookback_days": days,
        "benchmarks": exposures,
    }


def generate_volatility_cone_chart(
    *,
    symbol: str = "XAUUSD",
    days: int = 365,
    windows: Optional[Sequence[int]] = None,
    quantiles: Optional[Sequence[float]] = None,
    output_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Create a volatility cone chart and return summary statistics."""

    history = fetch_price_history(symbol, days=days)
    if history.empty:
        return {
            "symbol": symbol,
            "error": f"No historical data returned for {symbol} ({days} days lookback).",
        }

    base_output = Path(output_dir) if output_dir is not None else Path(__file__).resolve().parents[2] / "outputs"
    chart_path = plot_volatility_cone(history, base_output, symbol, windows, quantiles)
    if chart_path is None:
        return {
            "symbol": symbol,
            "error": "Unable to generate volatility cone due to insufficient data.",
        }

    returns = history["Close"].pct_change().dropna()
    window_set = tuple(sorted(set(windows or (5, 10, 20, 60, 120))))
    quantile_list = tuple(quantiles or (0.1, 0.5, 0.9))
    metrics: Dict[int, Dict[str, Any]] = {}

    for window in window_set:
        if window <= 1 or len(returns) < window:
            continue
        rolling_vol = returns.rolling(window).std().dropna() * math.sqrt(252)
        if rolling_vol.empty:
            continue
        metrics[window] = {
            "latest": float(rolling_vol.iloc[-1]),
            "quantiles": {
                f"q{int(q * 100)}": float(rolling_vol.quantile(q)) for q in quantile_list
            },
        }

    return {
        "symbol": symbol,
        "lookback_days": days,
        "chart_path": str(chart_path),
        "windows": [window for window in window_set if window in metrics],
        "metrics": metrics,
    }


__all__ = [
    "DEFAULT_FACTOR_SYMBOLS",
    "compute_factor_exposures",
    "prepare_quant_dataset",
    "generate_volatility_cone_chart",
]
