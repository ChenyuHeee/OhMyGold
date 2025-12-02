"""Adapter for retrieving FX-style price history from Alpha Vantage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import requests
from requests import Session

from .base import MarketDataAdapter
from ..exceptions import DataProviderError


@dataclass(frozen=True)
class _ParsedSymbol:
    base: str
    quote: str


def _parse_symbol(symbol: str) -> _ParsedSymbol:
    """Split symbols such as ``XAUUSD`` into base/quote legs."""

    sanitized = symbol.replace("/", "").strip().upper()
    if len(sanitized) < 6:
        raise DataProviderError(
            f"Alpha Vantage requires FX-style symbols like XAUUSD; got '{symbol}'"
        )
    base = sanitized[:3]
    quote = sanitized[3:6]
    if not base.isalpha() or not quote.isalpha():
        raise DataProviderError(
            f"Alpha Vantage symbol must contain only letters; got '{symbol}'"
        )
    return _ParsedSymbol(base=base, quote=quote)


class AlphaVantageFXAdapter(MarketDataAdapter):
    """Fetch OHLC price history from Alpha Vantage's FX_DAILY endpoint."""

    _API_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str]) -> None:
        self._api_key = api_key

    def fetch_price_history(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        session: Optional[Session] = None,
    ) -> pd.DataFrame:
        if not self._api_key:
            raise DataProviderError("Alpha Vantage API key not configured")

        parsed = _parse_symbol(symbol)
        params: Dict[str, str] = {
            "function": "FX_DAILY",
            "from_symbol": parsed.base,
            "to_symbol": parsed.quote,
            "outputsize": "full",
            "apikey": self._api_key,
        }
        requester = session.get if session else requests.get
        response = requester(self._API_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        time_series = payload.get("Time Series FX (Daily)")
        if not time_series:
            note = payload.get("Note") or payload.get("Information")
            if note:
                raise DataProviderError(f"Alpha Vantage throttled request: {note}")
            error_message = payload.get("Error Message")
            if error_message:
                raise DataProviderError(f"Alpha Vantage error: {error_message}")
            raise DataProviderError("Alpha Vantage response missing FX time series data")

        records = []
        for date_str, values in time_series.items():
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                open_price = float(values["1. open"])
                high_price = float(values["2. high"])
                low_price = float(values["3. low"])
                close_price = float(values["4. close"])
            except (KeyError, ValueError) as exc:
                raise DataProviderError(
                    f"Malformed Alpha Vantage FX data for {symbol} on {date_str}"
                ) from exc

            records.append(
                {
                    "Date": dt,
                    "Open": open_price,
                    "High": high_price,
                    "Low": low_price,
                    "Close": close_price,
                    "Adj Close": close_price,
                    "Volume": 0.0,
                }
            )

        if not records:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"])

        df = pd.DataFrame.from_records(records)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)

        start_date = pd.Timestamp(start.date())
        end_date = pd.Timestamp(end.date())
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        return df
