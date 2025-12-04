"""Base interfaces for market and news data adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterator, NamedTuple, Optional

try:  # Python 3.11+
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 not supported
    from typing_extensions import Literal  # type: ignore

import pandas as pd
from requests import Session


class MarketDataAdapter(ABC):
    """Abstract adapter for fetching OHLCV style market data."""

    @abstractmethod
    def fetch_price_history(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        session: Optional[Session] = None,
    ) -> pd.DataFrame:
        """Return price history for ``symbol`` in the given window."""


class NewsDataAdapter(ABC):
    """Abstract adapter for retrieving structured news or sentiment payloads."""

    @abstractmethod
    def fetch_sentiment(self, symbol: str, *, limit: int = 20) -> Dict[str, Any]:
        """Return sentiment payload for ``symbol``."""


@dataclass
class CacheConfig:
    """Cache configuration injected into adapters that support local persistence."""

    expire_after: timedelta
    namespace: str = "market"
    backend: Literal["memory", "sqlite", "redis"] = "sqlite"


@dataclass
class RetryConfig:
    """Retry configuration shared across adapters to standardize resilience."""

    total: int = 3
    backoff: float = 1.0
    jitter: float = 0.0


@dataclass
class QuoteSnapshot:
    """Latest quote context used for quick status checks and monitoring."""

    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    volume: Optional[float]
    timestamp: datetime
    provider: str


@dataclass
class QuoteTick:
    """Streaming tick information pushed from live providers."""

    price: float
    size: Optional[float]
    side: Literal["bid", "ask", "trade"]
    timestamp: datetime


class Capability(NamedTuple):
    """Capabilities reported by adapters so routers can route requests."""

    streaming: bool
    level2: bool
    historical: bool
    economic_calendar: bool = False


class StreamingHandle:
    """Lightweight handle returned by streaming subscriptions."""

    def __init__(self) -> None:
        self._active = True

    def close(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active


class DataSourceAdapter(MarketDataAdapter):
    """Extended adapter contract covering snapshots, streaming, and backtesting."""

    name: str = "generic"
    provider_type: Literal["live", "delayed", "historical", "mock"] = "live"

    def capability(self) -> Capability:
        return Capability(streaming=False, level2=False, historical=True)

    # Optional enhancements -------------------------------------------------
    def configure_cache(self, cache: CacheConfig) -> None:
        """Inject cache settings; default为 no-op。"""

    def configure_retry(self, retry: RetryConfig) -> None:
        """Inject retry settings; default为 no-op。"""

    def snapshot(self, symbol: str) -> QuoteSnapshot:
        """Return a quick snapshot; raise if provider无法支持。"""

        raise NotImplementedError(f"{self.__class__.__name__} 不支持快照接口")

    def stream_quotes(
        self,
        symbol: str,
        *,
        on_tick: Callable[[QuoteTick], None],
        on_disconnect: Optional[Callable[[Optional[Exception]], None]] = None,
    ) -> StreamingHandle:
        """Subscribe to live quotes; default抛出未实现。"""

        raise NotImplementedError(f"{self.__class__.__name__} 不支持实时订阅")

    def iter_backtest_bars(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        timeframe: str = "1d",
    ) -> Iterator[Dict[str, Any]]:
        """Yield bars for replay; default退化为一次性 fetch。"""

        frame = self.fetch_price_history(symbol, start=start, end=end)
        if frame.empty:
            return iter(())
        records = frame.to_dict(orient="records")
        timestamps = frame.index.to_pydatetime()
        enriched = []
        for idx, record in enumerate(records):
            payload = dict(record)
            payload["timestamp"] = timestamps[idx]
            payload["timeframe"] = timeframe
            enriched.append(payload)
        return iter(enriched)
