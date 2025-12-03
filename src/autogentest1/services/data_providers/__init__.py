"""Factory helpers for selecting configured market data providers."""

from __future__ import annotations

from .base import MarketDataAdapter, NewsDataAdapter
from .yfinance_adapter import YahooFinanceAdapter
from .alpha_vantage_adapter import AlphaVantageNewsAdapter
from .alpha_vantage_fx_adapter import AlphaVantageFXAdapter
from .ibkr_adapter import IBKRAdapter
from .tanshu_gold_adapter import TanshuGoldAdapter
from .twelvedata_adapter import TwelveDataAdapter
from .polygon_adapter import PolygonAdapter

__all__ = [
    "MarketDataAdapter",
    "NewsDataAdapter",
    "YahooFinanceAdapter",
    "AlphaVantageNewsAdapter",
    "AlphaVantageFXAdapter",
    "IBKRAdapter",
    "TanshuGoldAdapter",
    "TwelveDataAdapter",
    "PolygonAdapter",
]
