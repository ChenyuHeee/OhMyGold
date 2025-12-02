"""Unit tests for risk snapshot generation."""

from __future__ import annotations

import pandas as pd

from autogentest1.services.risk import RiskLimits, build_risk_snapshot


def test_build_risk_snapshot_empty_history() -> None:
    history = pd.DataFrame({"Close": []})
    limits = RiskLimits(max_position_oz=5000, stress_var_millions=3.0, daily_drawdown_pct=3.0)

    snapshot = build_risk_snapshot(
        "XAUUSD",
        history,
        limits=limits,
        current_position_oz=1000,
        pnl_today_millions=-0.2,
    )

    assert snapshot["limit_position_oz"] == 5000
    assert snapshot["drawdown_alert"] is False
