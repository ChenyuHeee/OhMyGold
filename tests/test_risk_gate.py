"""Tests for the hard risk gate enforcement layer."""

from __future__ import annotations

from typing import Any

from autogentest1.config.settings import Settings
from autogentest1.services.risk_gate import enforce_hard_limits


def _base_settings(**overrides: Any) -> Settings:
    return Settings(deepseek_api_key="test-key", **overrides)


def _build_response(include_stop: bool = True) -> dict[str, object]:
    orders = [
        {
            "instrument": "XAUUSD",
            "side": "SELL",
            "size_oz": 1000,
            "type": "LIMIT",
            "entry": 4200,
        }
    ]
    if include_stop:
        orders.append(
            {
                "instrument": "XAUUSD",
                "side": "BUY",
                "size_oz": 1000,
                "type": "STOP",
                "entry": 4220,
            }
        )
    return {
        "details": {
            "execution_checklist": {
                "orders": orders,
            },
            "risk_compliance_signoff": {
                "risk_metrics": {
                    "position_utilization": 0.4,
                    "stress_test_worst_loss_millions": -0.8,
                }
            },
        }
    }


def _base_context() -> dict[str, object]:
    return {
        "risk_snapshot": {
            "position_utilization": 0.25,
            "pnl_today_millions": 0.2,
            "drawdown_threshold_millions": -0.3,
            "risk_alerts": [],
            "cross_asset_correlations": [],
        }
    }


def test_enforce_hard_limits_no_violation() -> None:
    settings = _base_settings()
    response = _build_response()
    context = _base_context()

    report = enforce_hard_limits(response, context=context, settings=settings)

    assert report.breached is False
    assert report.violations == []


def test_enforce_hard_limits_drawdown_violation() -> None:
    settings = _base_settings()
    response = _build_response()
    context = _base_context()
    context["risk_snapshot"]["pnl_today_millions"] = -0.5
    context["risk_snapshot"]["drawdown_threshold_millions"] = -0.3

    report = enforce_hard_limits(response, context=context, settings=settings)

    assert report.breached is True
    codes = {violation.code for violation in report.violations}
    assert "DAILY_DRAWDOWN" in codes


def test_enforce_hard_limits_requires_stop_loss() -> None:
    settings = _base_settings()
    response = _build_response(include_stop=False)
    context = _base_context()

    report = enforce_hard_limits(response, context=context, settings=settings)

    assert report.breached is True
    assert any(violation.code == "STOP_LOSS_MISSING" for violation in report.violations)