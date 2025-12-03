"""Compliance helper exposed via ToolsProxy."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from ..config.settings import Settings, get_settings
from ..services.compliance import evaluate_compliance
from ..services.risk import RiskLimits


def run_compliance_checks(
    plan: Mapping[str, Any],
    *,
    current_position_oz: Optional[float] = None,
    limits: Optional[RiskLimits] = None,
    settings: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Execute structural compliance checks over a proposed trade plan."""

    effective_settings = settings or get_settings()
    effective_limits = limits or RiskLimits(
        max_position_oz=effective_settings.max_position_oz,
        stress_var_millions=effective_settings.stress_var_millions,
        daily_drawdown_pct=effective_settings.daily_drawdown_pct,
    )

    position = current_position_oz if current_position_oz is not None else effective_settings.default_position_oz
    return evaluate_compliance(
        plan,
        current_position_oz=position,
        limits=effective_limits,
        settings=effective_settings,
    )


__all__ = ["run_compliance_checks"]
