"""Market data retrieval utilities."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import pandas as pd
import yfinance as yf

from ..utils.logging import get_logger
from ..utils.serialization import df_to_records
from .indicators import compute_indicators

logger = get_logger(__name__)


def fetch_price_history(symbol: str, days: int = 14) -> pd.DataFrame:
    """Fetch recent price history for the given symbol using yfinance."""

    end = datetime.utcnow()
    start = end - timedelta(days=days * 2)
    logger.info("Downloading price history for %s", symbol)
    data = yf.download(symbol, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
    if data.empty:
        logger.warning("No price data retrieved for %s", symbol)
        return data
    data = data.tail(days)
    data.index = pd.to_datetime(data.index)
    return data


def latest_quote(symbol: str) -> Optional[float]:
    """Return the latest close price for quick status updates."""

    history = fetch_price_history(symbol, days=1)
    if history.empty:
        return None
    return float(history["Close"].iloc[-1])


def price_history_payload(symbol: str, days: int = 14) -> Dict[str, Any]:
    """Return a JSON-serializable payload describing price history."""

    history = fetch_price_history(symbol, days=days)
    return {
        "symbol": symbol,
        "lookback_days": days,
        "frequency": "daily",
        "records": df_to_records(history.tail(days), include_index=True),
    }


def market_snapshot(symbol: str, days: int = 30) -> Dict[str, Any]:
    """Return key market metrics such as latest price and volatility."""

    history = fetch_price_history(symbol, days=days)
    indicators = compute_indicators(history)
    latest_close = float(history["Close"].iloc[-1]) if not history.empty else None

    atr_series = indicators.get("atr_14")
    atr_latest = float(atr_series.iloc[-1]) if atr_series is not None and not atr_series.empty else None

    return {
        "symbol": symbol,
        "latest_close": latest_close,
        "atr_14": atr_latest,
        "history_sample": df_to_records(history.tail(5), include_index=True),
    }
