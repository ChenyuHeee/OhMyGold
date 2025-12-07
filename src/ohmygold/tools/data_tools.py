"""Data-oriented helper functions designed for ToolProxy invocation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

try:  # pragma: no cover
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ImportError("The 'pandas' package is required for data tool helpers.") from exc

from ..config.settings import get_settings
from ..services.market_data import fetch_price_history, market_snapshot
from ..services.indicators import compute_indicators
from ..services.sentiment import collect_sentiment_snapshot
from ..utils.serialization import df_to_records
from ..utils.logging import get_logger

logger = get_logger(__name__)


def get_gold_market_snapshot(symbol: str = "XAUUSD", days: int = 30) -> Dict[str, Any]:
    """Return a comprehensive snapshot for gold including price and indicator metrics."""

    snapshot = market_snapshot(symbol, days=days)
    history = fetch_price_history(symbol, days=days)
    indicators = compute_indicators(history)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "market": snapshot,
        "indicators": {
            name: [float(value) if not pd.isna(value) else None for value in series.tail(10)]
            for name, series in indicators.items()
        },
    }


def _fetch_series_with_fallback(
    candidates: Iterable[Tuple[str, str]],
    days: int,
) -> Optional[Tuple[str, str, pd.Series, pd.Series]]:
    """Return aligned close series for the first successful symbol pair."""

    for gold_symbol, silver_symbol in candidates:
        try:
            gold_history = fetch_price_history(gold_symbol, days=days)
            silver_history = fetch_price_history(silver_symbol, days=days)
        except Exception as exc:  # pragma: no cover - defensive guard for provider errors
            logger.warning(
                "获取金银比行情失败：%s/%s -> %s", gold_symbol, silver_symbol, exc
            )
            continue

        if gold_history.empty or silver_history.empty:
            logger.info(
                "金银比行情为空，尝试下一组合：%s/%s", gold_symbol, silver_symbol
            )
            continue

        merged = pd.DataFrame(
            {
                "gold": gold_history["Close"],
                "silver": silver_history["Close"],
            }
        ).dropna()
        if merged.empty:
            logger.info(
                "金银比闭盘数据缺失，尝试下一组合：%s/%s", gold_symbol, silver_symbol
            )
            continue

        return gold_symbol, silver_symbol, merged["gold"], merged["silver"]

    return None


def get_gold_silver_ratio(days: int = 60) -> Dict[str, Any]:
    """Calculate the gold/silver ratio using the shared market data pipeline."""

    symbol_pairs: Tuple[Tuple[str, str], ...] = (
        ("XAUUSD", "XAGUSD"),
        ("GC=F", "SI=F"),
        ("GLD", "SLV"),
    )

    result = _fetch_series_with_fallback(symbol_pairs, days)
    if result is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": "Unable to source gold/silver prices via configured providers",
        }

    gold_symbol, silver_symbol, gold_series, silver_series = result
    ratio_series = gold_series / silver_series
    ratio_series = ratio_series.dropna()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pair": {"gold": gold_symbol, "silver": silver_symbol},
        "series": [
            {
                "date": index.strftime("%Y-%m-%d"),
                "ratio": float(value) if not pd.isna(value) else None,
            }
            for index, value in ratio_series.tail(30).items()
        ],
        "latest": float(ratio_series.iloc[-1]) if not ratio_series.empty else None,
    }


def get_macro_snapshot() -> Dict[str, Any]:
    """Collect macro proxies such as DXY and 10Y real yields (TIPS)."""

    def _first_available(symbols: Iterable[str], days: int) -> Tuple[Optional[str], pd.DataFrame]:
        for symbol in symbols:
            try:
                history = fetch_price_history(symbol, days=days)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning("宏观行情抓取失败：%s -> %s", symbol, exc)
                continue
            if not history.empty:
                return symbol, history
        return None, pd.DataFrame()

    dxy_symbol, dxy_history = _first_available(("DX-Y.NYB", "DXY", "DX-Y"), days=45)
    tip_symbol, tip_history = _first_available(("TIP", "IEF"), days=45)

    result: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "usd_index": {
            "symbol": dxy_symbol,
            "records": df_to_records(dxy_history.tail(10), include_index=True),
        },
        "tips_etf": {
            "symbol": tip_symbol,
            "records": df_to_records(tip_history.tail(10), include_index=True),
        },
    }
    return result


def get_event_calendar() -> Dict[str, Any]:
    """Placeholder economic calendar to be replaced with real provider."""

    today = datetime.now(timezone.utc).date().isoformat()
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
