"""Polygon.io market data adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from requests import Session

from ..exceptions import DataProviderError
from .base import MarketDataAdapter

try:  # pragma: no cover - optional dependency resolution handled at runtime
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore


class PolygonAdapter(MarketDataAdapter):
    """Fetch daily aggregates from Polygon.io."""

    def __init__(
        self,
        api_key: Optional[str],
        *,
        base_url: str = "https://api.polygon.io",
        symbol_map: Optional[Dict[str, str]] = None,
    ) -> None:
        if not api_key:
            raise DataProviderError("Polygon API key 未配置，请设置 settings.polygon_api_key")
        if requests is None:
            raise DataProviderError("requests 库不可用，无法调用 Polygon 接口")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.symbol_map = {str(key).upper(): str(value) for key, value in (symbol_map or {}).items()}

    def _resolve_symbol(self, symbol: str) -> str:
        mapped = self.symbol_map.get(symbol.upper())
        return mapped or symbol

    def fetch_price_history(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        session: Optional[Session] = None,
    ) -> pd.DataFrame:
        ticker = self._resolve_symbol(symbol)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        url = f"{self.base_url}/v2/aggs/ticker/{ticker}/range/1/day/{start_str}/{end_str}"
        params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self.api_key}
        client = session or requests
        try:  # pragma: no cover - exercises live HTTP path during integration testing
            response = client.get(url, params=params, timeout=6)  # type: ignore[call-arg]
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover
            raise DataProviderError(f"Polygon 数据获取失败：{exc}") from exc

        if not isinstance(payload, dict):
            raise DataProviderError("Polygon 返回格式异常")

        status = payload.get("status")
        if status != "OK":
            error = payload.get("error") or payload.get("message") or "未知错误"
            raise DataProviderError(f"Polygon 返回错误：{error}")

        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"])

        records = []
        for item in results:
            if not isinstance(item, dict):
                continue
            ts = item.get("t")
            try:
                timestamp = datetime.utcfromtimestamp(int(ts) / 1000)
            except Exception:
                continue
            records.append(
                {
                    "Date": timestamp,
                    "Open": float(item.get("o", 0.0)),
                    "High": float(item.get("h", 0.0)),
                    "Low": float(item.get("l", 0.0)),
                    "Close": float(item.get("c", 0.0)),
                    "Adj Close": float(item.get("c", 0.0)),
                    "Volume": float(item.get("v", 0.0)),
                }
            )

        if not records:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"])

        frame = pd.DataFrame.from_records(records)
        frame.set_index("Date", inplace=True)
        frame.sort_index(inplace=True)
        return frame


__all__ = ["PolygonAdapter"]
