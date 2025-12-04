"""Router for selecting appropriate data source adapters at runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from .data_providers import CacheConfig, DataSourceAdapter, QuoteSnapshot, RetryConfig
from .exceptions import DataProviderError


@dataclass
class DataSourceRouter:
    """Manage multiple data source adapters across live, mock and backtest modes."""

    adapters: Dict[str, DataSourceAdapter] = field(default_factory=dict)
    mode: str = "live"
    cache_config: Optional[CacheConfig] = None
    retry_config: Optional[RetryConfig] = None

    def register(self, key: str, adapter: DataSourceAdapter) -> None:
        normalized = key.strip().lower()
        if self.cache_config is not None:
            adapter.configure_cache(self.cache_config)
        if self.retry_config is not None:
            adapter.configure_retry(self.retry_config)
        self.adapters[normalized] = adapter

    def set_mode(self, mode: str) -> None:
        normalized = mode.strip().lower()
        if normalized not in {"live", "mock", "backtest", "delayed"}:
            raise ValueError(f"Unsupported data mode: {mode}")
        self.mode = normalized

    def configure_cache(self, cache: CacheConfig) -> None:
        self.cache_config = cache
        for adapter in self.adapters.values():
            adapter.configure_cache(cache)

    def configure_retry(self, retry: RetryConfig) -> None:
        self.retry_config = retry
        for adapter in self.adapters.values():
            adapter.configure_retry(retry)

    def _select(self, *, prefer: Optional[str] = None) -> DataSourceAdapter:
        if prefer:
            key = prefer.lower()
            if key in self.adapters:
                return self.adapters[key]
        if self.mode in self.adapters:
            return self.adapters[self.mode]
        if "live" in self.adapters:
            return self.adapters["live"]
        if self.adapters:
            return next(iter(self.adapters.values()))
        raise DataProviderError("No data source adapter registered")

    def fetch_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        *,
        timeframe: str = "1d",
        prefer: Optional[str] = None,
        **adapter_kwargs,
    ) -> pd.DataFrame:
        adapter = self._select(prefer=prefer)
        frame = adapter.fetch_price_history(symbol, start=start, end=end, **adapter_kwargs)
        if timeframe.lower() in {"1h", "4h", "1m"}:
            # 简化：如需频率转换，使用 pandas resample
            rule_map = {"1h": "1H", "4h": "4H", "1m": "1T"}
            rule = rule_map[timeframe.lower()]
            frame = frame.resample(rule).agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Adj Close": "last",
                    "Volume": "sum",
                }
            ).dropna(how="all")
        return frame

    def snapshot(self, symbol: str, *, prefer: Optional[str] = None) -> QuoteSnapshot:
        adapter = self._select(prefer=prefer)
        return adapter.snapshot(symbol)
