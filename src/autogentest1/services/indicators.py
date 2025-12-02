"""Technical indicator calculations."""

from __future__ import annotations

from typing import Dict

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange


def compute_indicators(history: pd.DataFrame) -> Dict[str, pd.Series]:
    """Compute a collection of standard technical indicators."""

    if history.empty:
        return {}

    close = history["Close"].astype(float)

    indicators: Dict[str, pd.Series] = {
        "sma_20": SMAIndicator(close, window=20, fillna=True).sma_indicator(),
        "sma_50": SMAIndicator(close, window=50, fillna=True).sma_indicator(),
        "rsi_14": RSIIndicator(close, window=14, fillna=True).rsi(),
    }

    atr = AverageTrueRange(
        high=history["High"].astype(float),
        low=history["Low"].astype(float),
        close=close,
        window=14,
        fillna=True,
    )
    indicators["atr_14"] = atr.average_true_range()

    macd = MACD(close, window_slow=26, window_fast=12, window_sign=9, fillna=True)
    indicators.update(
        {
            "macd": macd.macd(),
            "macd_signal": macd.macd_signal(),
            "macd_diff": macd.macd_diff(),
        }
    )

    bb = BollingerBands(close, window=20, window_dev=2.0, fillna=True)
    indicators.update(
        {
            "bb_high": bb.bollinger_hband(),
            "bb_low": bb.bollinger_lband(),
            "bb_mavg": bb.bollinger_mavg(),
        }
    )

    return indicators
