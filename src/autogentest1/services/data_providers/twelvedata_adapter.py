"""Adapter for the Twelve Data time-series API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd
import requests
from requests import Session

from .base import DataSourceAdapter
from ..exceptions import DataProviderError


def _to_float(value: object) -> Optional[float]:
    """Coerce loosely formatted numeric values to floats."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


class TwelveDataAdapter(DataSourceAdapter):
    """Fetch OHLCV candles from Twelve Data."""

    _DEFAULT_BASE_URL = "https://api.twelvedata.com"

    def __init__(
        self,
        api_key: Optional[str],
        *,
        base_url: Optional[str] = None,
        symbol_map: Optional[Dict[str, str]] = None,
        default_symbol: Optional[str] = None,
    ) -> None:
        if not api_key:
            raise DataProviderError("未配置 Twelve Data API 密钥")
        self._api_key = api_key
        self._base_url = (base_url or self._DEFAULT_BASE_URL).rstrip("/")
        self._symbol_map = {
            (key or "").upper(): (value or "").strip()
            for key, value in (symbol_map or {}).items()
            if isinstance(key, str) and value is not None
        }
        self._default_symbol = (default_symbol or "").strip()

    def fetch_price_history(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        session: Optional[Session] = None,
    ) -> pd.DataFrame:
        def _utc_naive(moment: datetime) -> datetime:
            if moment.tzinfo is None:
                return moment
            return moment.astimezone(timezone.utc).replace(tzinfo=None)

        start_utc = _utc_naive(start)
        end_utc = _utc_naive(end)

        resolved_symbol = self._resolve_symbol(symbol)
        if not resolved_symbol:
            raise DataProviderError(f"Twelve Data 未找到 {symbol} 对应的交易代码")

        url = f"{self._base_url}/time_series"
        output_size = max(100, min(5000, (end_utc - start_utc).days + 50))
        params = {
            "symbol": resolved_symbol,
            "interval": "1day",
            "start_date": start_utc.strftime("%Y-%m-%d"),
            "end_date": end_utc.strftime("%Y-%m-%d"),
            "outputsize": output_size,
            "order": "ASC",
            "timezone": "UTC",
            "apikey": self._api_key,
        }

        requester = session.get if session else requests.get
        try:
            response = requester(url, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:  # pragma: no cover - live call
            raise DataProviderError(f"Twelve Data 请求失败：{exc}") from exc
        except ValueError as exc:
            raise DataProviderError("Twelve Data 返回了无法解析的JSON") from exc

        if isinstance(payload, dict) and payload.get("status") == "error":
            message = payload.get("message") or payload.get("error") or "Twelve Data 返回错误"
            raise DataProviderError(message)

        values = payload.get("values") if isinstance(payload, dict) else None
        if not values:
            raise DataProviderError("Twelve Data 返回空行情数据")

        records = []
        for entry in values:
            if not isinstance(entry, dict):
                continue
            timestamp = entry.get("datetime")
            if not isinstance(timestamp, str):
                continue
            ts = pd.to_datetime(timestamp, utc=True, errors="coerce")
            if pd.isna(ts):
                continue
            ts = ts.to_pydatetime().replace(tzinfo=None)

            close_price = _to_float(entry.get("close"))
            if close_price is None:
                continue
            open_price = _to_float(entry.get("open")) or close_price
            high_price = _to_float(entry.get("high")) or close_price
            low_price = _to_float(entry.get("low")) or close_price
            volume = _to_float(entry.get("volume"))
            if volume is None:
                volume = float("nan")

            records.append(
                {
                    "Date": ts,
                    "Open": open_price,
                    "High": high_price,
                    "Low": low_price,
                    "Close": close_price,
                    "Adj Close": close_price,
                    "Volume": volume,
                }
            )

        if not records:
            raise DataProviderError("Twelve Data 行情记录无法解析")

        df = pd.DataFrame.from_records(records)
        df.sort_values("Date", inplace=True)
        df.set_index("Date", inplace=True)
        df.index.name = "Date"
        return df.loc[(df.index >= start_utc) & (df.index <= end_utc)]

    def _resolve_symbol(self, symbol: str) -> str:
        symbol_norm = (symbol or "").upper()
        candidates = {
            symbol_norm,
            symbol_norm.replace("=", ""),
            symbol_norm.replace("/", ""),
            symbol_norm.replace("-", ""),
        }
        for candidate in candidates:
            mapped = self._symbol_map.get(candidate)
            if mapped:
                return mapped
        if self._default_symbol:
            return self._default_symbol
        return symbol or ""
