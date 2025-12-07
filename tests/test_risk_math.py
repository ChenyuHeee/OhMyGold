"""Unit tests for risk_math analytical helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from ohmygold.services.risk_math import (
    ScenarioShock,
    apply_scenario,
    historical_var,
    rolling_correlation,
)


def test_rolling_correlation_raises_for_small_window() -> None:
    series = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        rolling_correlation(series, series, window=1)


def test_rolling_correlation_basic_alignment() -> None:
    series_a = pd.Series([1, 2, 3, 4, 5, 6], dtype=float)
    series_b = pd.Series([2, 4, 6, 8, 10, 12], dtype=float)
    result = rolling_correlation(series_a, series_b, window=3)
    # Perfect linear relationship should converge toward 1.0 where defined.
    assert not result.dropna().empty
    assert abs(result.dropna().iloc[-1] - 1.0) < 1e-6


def test_historical_var_quantile() -> None:
    returns = pd.Series([-0.05, -0.02, -0.03, 0.01, 0.015, -0.025, 0.02])
    var_95 = historical_var(returns, confidence=0.95)
    assert var_95 < 0  # VaR should be a loss
    assert var_95 <= -0.02


def test_apply_scenario_projects_levels() -> None:
    series = pd.Series([1900.0, 1920.0, 1910.0])
    shocks = [
        ScenarioShock(label="minus1", pct_change=-0.01),
        ScenarioShock(label="flat", pct_change=0.0),
        ScenarioShock(label="plus1", pct_change=0.01),
    ]
    projections = apply_scenario(series, shocks)
    assert projections == [
        ("minus1", pytest.approx(1910.0 * 0.99)),
        ("flat", pytest.approx(1910.0)),
        ("plus1", pytest.approx(1910.0 * 1.01)),
    ]


