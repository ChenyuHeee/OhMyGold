"""Tests for compliance evaluation utilities."""

from __future__ import annotations

from ohmygold.config.settings import Settings
from ohmygold.services.compliance import evaluate_compliance
from ohmygold.services.risk import RiskLimits
from ohmygold.tools.compliance_tools import run_compliance_checks


def test_evaluate_compliance_detects_single_order_breach() -> None:
    settings = Settings(  # type: ignore[call-arg]
        deepseek_api_key="test-key",
        compliance_max_single_order_oz=1000.0,
        max_position_oz=2000.0,
    )
    limits = RiskLimits(
        max_position_oz=settings.max_position_oz,
        stress_var_millions=settings.stress_var_millions,
        daily_drawdown_pct=settings.daily_drawdown_pct,
    )
    plan = {
        "orders": [
            {
                "instrument": "XAUUSD",
                "side": "buy",
                "size_oz": 1500,
                "stop": 2320,
                "target": 2400,
                "counterparty": "CME",
            }
        ]
    }

    result = evaluate_compliance(plan, current_position_oz=200.0, limits=limits, settings=settings)
    assert result["orders_checked"] == 1
    assert "exceeds_single_order_limit" in result["order_reports"][0]["violations"]
    assert "projected_position_limit_breach" not in result["violations"]


def test_evaluate_compliance_requires_stop_loss() -> None:
    settings = Settings(deepseek_api_key="test-key")  # type: ignore[call-arg]
    plan = {
        "orders": [
            {
                "instrument": "GC",
                "side": "buy",
                "size_oz": 100,
                "target": 2400,
                "counterparty": "CME",
            }
        ]
    }

    result = evaluate_compliance(plan, current_position_oz=0.0, settings=settings)
    assert "missing_stop_loss" in result["order_reports"][0]["violations"]


def test_run_compliance_checks_wrapper_uses_settings() -> None:
    settings = Settings(  # type: ignore[call-arg]
        deepseek_api_key="test-key",
        compliance_allowed_counterparties=["CME"],
    )
    plan = {
        "orders": [
            {
                "instrument": "GLD",
                "side": "sell",
                "size_oz": 50,
                "stop": 175,
                "target": 160,
                "counterparty": "CME",
            }
        ]
    }

    result = run_compliance_checks(plan, settings=settings, current_position_oz=25.0)
    assert result["violations"] == []
    assert result["orders_checked"] == 1
    assert result["projected_position_oz"] == -25.0
