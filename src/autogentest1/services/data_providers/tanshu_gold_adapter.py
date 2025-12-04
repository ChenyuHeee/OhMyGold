"""Adapter for the Tanshu (探数) gold market API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

import pandas as pd
import requests
from requests import Session
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None  # type: ignore[assignment]

from .base import DataSourceAdapter
from ..exceptions import DataProviderError


def _to_float(value: object) -> Optional[float]:
    """Convert loosely formatted numeric strings to floats."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned in {"-", "--"}:
            return None
        cleaned = cleaned.replace(",", "")
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


class TanshuGoldAdapter(DataSourceAdapter):
    """Fetch spot or exchange gold quotes from Tanshu's gold endpoints."""

    _BASE_URL = "https://api.tanshuapi.com/api/gold/v1"

    def __init__(
        self,
        api_key: Optional[str],
        *,
        endpoint: Optional[str] = None,
        symbol_map: Optional[Dict[str, str]] = None,
        default_symbol_code: Optional[str] = None,
    ) -> None:
        if not api_key:
            raise DataProviderError("未配置探数API密钥")
        self._api_key = api_key
        self._endpoint = (endpoint or "gjgold2").strip("/")
        self._symbol_map = {
            (key or "").upper(): (value or "").strip()
            for key, value in (symbol_map or {}).items()
            if isinstance(key, str)
        }
        self._default_symbol_code = (default_symbol_code or "").strip()

    # pylint: disable=too-many-locals
    def fetch_price_history(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        session: Optional[Session] = None,
    ) -> pd.DataFrame:
        requester = session.get if session else requests.get
        url = f"{self._BASE_URL}/{self._endpoint}"
        try:
            response = requester(url, params={"key": self._api_key}, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:  # pragma: no cover - live call
            raise DataProviderError(f"探数接口请求失败：{exc}") from exc
        except ValueError as exc:  # payload.json() failure
            raise DataProviderError("探数接口返回了无法解析的JSON") from exc

        if payload.get("code") != 1:
            message = payload.get("msg") or "探数接口返回错误"
            raise DataProviderError(message)

        data = payload.get("data") or {}
        listing = data.get("list")
        if listing is None:
            raise DataProviderError("探数接口未返回行情列表数据")

        entry = self._find_entry(listing, symbol)
        if entry is None:
            raise DataProviderError(f"探数接口未找到 {symbol} 对应的行情条目")

        close_price = _to_float(entry.get("price"))
        if close_price is None:
            raise DataProviderError("探数行情缺少有效的最新价格")

        open_price = _to_float(entry.get("openingprice")) or close_price
        high_price = _to_float(entry.get("maxprice")) or close_price
        low_price = _to_float(entry.get("minprice")) or close_price
        adj_close = close_price

        volume_candidates = (
            entry.get("tradeamount"),
            entry.get("volume"),
            entry.get("holdamount"),
        )
        volume = 0.0
        for candidate in volume_candidates:
            numeric = _to_float(candidate)
            if numeric is not None:
                volume = numeric
                break

        timestamp = self._parse_timestamp(entry.get("updatetime"))

        record = {
            "Open": open_price,
            "High": high_price,
            "Low": low_price,
            "Close": close_price,
            "Adj Close": adj_close,
            "Volume": volume,
        }

        df = pd.DataFrame([record])
        df.index = pd.to_datetime([timestamp])
        df.index.name = "Date"
        return df.loc[(df.index >= start) & (df.index <= end)]

    def _find_entry(self, listing: object, symbol: str) -> Optional[Dict[str, object]]:
        """Locate the entry matching the requested symbol."""

        candidates = list(self._candidate_codes(symbol))

        if isinstance(listing, dict):
            for code in candidates:
                if code and code in listing and isinstance(listing[code], dict):
                    return listing[code]
            # Sometimes the dict keys are arbitrary but values contain ``type`` fields.
            for value in listing.values():
                if isinstance(value, dict) and self._matches_entry(value, candidates):
                    return value
            return None

        if isinstance(listing, list):
            for item in listing:
                if isinstance(item, dict) and self._matches_entry(item, candidates):
                    return item

        return None

    def _candidate_codes(self, symbol: str) -> Iterable[str]:
        symbol_norm = (symbol or "").upper()
        stripped = symbol_norm.replace("/", "")
        mapped = self._symbol_map.get(symbol_norm) or self._symbol_map.get(stripped)
        default = self._default_symbol_code.upper() if self._default_symbol_code else ""
        return [
            mapped or "",
            default,
            symbol_norm,
            stripped,
            symbol_norm[:3],
        ]

    @staticmethod
    def _matches_entry(entry: Dict[str, object], candidates: Iterable[str]) -> bool:
        entry_type = str(entry.get("type", "")).upper()
        entry_name = str(entry.get("typename", "")).upper()
        for code in candidates:
            if not code:
                continue
            code_upper = code.upper()
            if entry_type == code_upper or code_upper in entry_name:
                return True
        return False

    @staticmethod
    def _parse_timestamp(value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(value, fmt)
                    if ZoneInfo is not None:
                        try:
                            # Tanshu timestamps are released in Beijing time (UTC+8).
                            parsed = (
                                parsed.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                                .astimezone(ZoneInfo("UTC"))
                                .replace(tzinfo=None)
                            )
                        except Exception:  # pragma: no cover - defensive guard
                            pass
                    return parsed
                except ValueError:
                    continue
        # Fallback to current time so downstream freshness checks still work briefly.
        now_utc = datetime.now(timezone.utc).replace(microsecond=0)
        return now_utc.replace(tzinfo=None)