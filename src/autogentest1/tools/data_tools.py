"""Data-oriented helper functions designed for ToolProxy invocation."""

from __future__ import annotations

from datetime import datetime
from importlib import import_module
from typing import Any, Dict

try:  # pragma: no cover
    pd = import_module("pandas")
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ImportError("The 'pandas' package is required for data tool helpers.") from exc

from ..config.settings import get_settings
from ..services.market_data import fetch_price_history, market_snapshot
from ..services.indicators import compute_indicators
from ..services.sentiment import collect_sentiment_snapshot
from ..utils.serialization import df_to_records


def get_gold_market_snapshot(symbol: str = "XAUUSD", days: int = 30) -> Dict[str, Any]:
    """Return a comprehensive snapshot for gold including price and indicator metrics."""

    snapshot = market_snapshot(symbol, days=days)
    history = fetch_price_history(symbol, days=days)
    indicators = compute_indicators(history)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "market": snapshot,
        "indicators": {
            name: [float(value) if not pd.isna(value) else None for value in series.tail(10)]
            for name, series in indicators.items()
        },
    }


def get_gold_silver_ratio(days: int = 60) -> Dict[str, Any]:
    """Calculate the gold/silver ratio using GLD and SLV ETFs as proxies."""

    try:  # pragma: no cover
        yf = import_module("yfinance")
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ImportError("The 'yfinance' package is required for gold/silver ratio.") from exc

    gold = yf.download("GLD", period=f"{days}d")
    silver = yf.download("SLV", period=f"{days}d")

    if gold.empty or silver.empty:
        return {"error": "Unable to download GLD/SLV data"}

    ratio = gold["Close"] / silver["Close"]

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "series": [
            {
                "date": index.strftime("%Y-%m-%d"),
                "ratio": float(value) if not pd.isna(value) else None,
            }
            for index, value in ratio.tail(30).items()
        ],
        "latest": float(ratio.iloc[-1]) if not pd.isna(ratio.iloc[-1]) else None,
    }


def get_macro_snapshot() -> Dict[str, Any]:
    """Collect macro proxies such as DXY and 10Y real yields (TIPS)."""

    try:  # pragma: no cover
        yf = import_module("yfinance")
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ImportError("The 'yfinance' package is required for macro snapshot.") from exc

    dxy = yf.download("DX-Y.NYB", period="30d")
    tips = yf.download("TIP", period="30d")

    result: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "usd_index": df_to_records(dxy.tail(10), include_index=True),
        "tips_etf": df_to_records(tips.tail(10), include_index=True),
    }
    return result


def get_event_calendar() -> Dict[str, Any]:
    """Placeholder economic calendar to be replaced with real provider."""

    today = datetime.utcnow().date().isoformat()
    return {
        "date": today,
        "events": [
            {
                "time_utc": f"{today}T13:30:00",
                "event": "Initial Jobless Claims",
                "importance": "medium",
            },
            {
                "time_utc": f"{today}T19:00:00",
                "event": "FOMC Member Speech",
                "importance": "high",
            },
        ],
    }


def get_news_sentiment(symbol: str = "XAUUSD") -> Dict[str, Any]:
    """Expose weighted news sentiment so agents can quantify narrative risk."""

    settings = get_settings()
    return collect_sentiment_snapshot(
        symbol,
        news_api_key=settings.news_api_key,
        alpha_vantage_api_key=settings.alpha_vantage_api_key,
    )
