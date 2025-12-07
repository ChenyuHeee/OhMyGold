"""Analytical helpers for advanced risk evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class ScenarioShock:
    """Represents a deterministic shock applied during scenario analysis."""

    label: str
    pct_change: float


def rolling_correlation(series_a: pd.Series, series_b: pd.Series, window: int = 20) -> pd.Series:
    """Compute rolling correlation with basic input sanitisation."""

    if window <= 1:
        raise ValueError("window must be greater than 1")
    aligned = pd.concat([series_a, series_b], axis=1).dropna()
    if aligned.empty:
        return pd.Series(dtype=float)
    return aligned.iloc[:, 0].rolling(window).corr(aligned.iloc[:, 1])


def historical_var(returns: pd.Series, confidence: float = 0.99) -> float:
    """Historical Value-at-Risk (one-period) expressed as a negative number."""

    if returns.empty:
        return float("nan")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return float(np.nanpercentile(returns.dropna(), (1 - confidence) * 100))


def apply_scenario(base_levels: pd.Series, shocks: Iterable[ScenarioShock]) -> List[Tuple[str, float]]:
    """Apply percentage shocks to a scalar level and return projected outcomes."""

    if base_levels.empty:
        return []
    latest = float(base_levels.iloc[-1])
    projections: List[Tuple[str, float]] = []
    for shock in shocks:
        projected = latest * (1 + shock.pct_change)
        projections.append((shock.label, projected))
    return projections
