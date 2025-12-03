"""Compliance rule evaluation utilities for trade plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..config.settings import Settings, get_settings
from ..services.risk import RiskLimits
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ComplianceConfig:
    """Configuration backing the compliance rule checks."""

    allowed_instruments: Sequence[str]
    restricted_instruments: Sequence[str]
    allowed_counterparties: Sequence[str]
    restricted_counterparties: Sequence[str]
    max_single_order_oz: float
    require_stop_loss: bool
    require_take_profit: bool


def _normalise_token(value: Any) -> str:
    if value is None:
        return ""
    token = str(value).strip()
    return token.upper()


def _extract_orders(plan: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    orders = plan.get("orders")
    if isinstance(orders, Mapping):
        return [orders]
    if isinstance(orders, Iterable):
        collected: List[Mapping[str, Any]] = []
        for item in orders:
            if isinstance(item, Mapping):
                collected.append(item)
        return collected
    return []


def build_compliance_config(settings: Settings) -> ComplianceConfig:
    """Construct a compliance configuration from application settings."""

    allowed_instruments = tuple(_normalise_token(item) for item in settings.compliance_allowed_instruments)
    restricted_instruments = tuple(_normalise_token(item) for item in settings.compliance_restricted_instruments)
    allowed_counterparties = tuple(_normalise_token(item) for item in settings.compliance_allowed_counterparties)
    restricted_counterparties = tuple(_normalise_token(item) for item in settings.compliance_restricted_counterparties)

    return ComplianceConfig(
        allowed_instruments=allowed_instruments,
        restricted_instruments=restricted_instruments,
        allowed_counterparties=allowed_counterparties,
        restricted_counterparties=restricted_counterparties,
        max_single_order_oz=float(settings.compliance_max_single_order_oz),
        require_stop_loss=bool(settings.compliance_require_stop_loss),
        require_take_profit=bool(settings.compliance_require_take_profit),
    )


def evaluate_compliance(
    plan: Mapping[str, Any],
    *,
    current_position_oz: float = 0.0,
    limits: Optional[RiskLimits] = None,
    settings: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Evaluate a trade plan against compliance guardrails."""

    effective_settings = settings or get_settings()
    config = build_compliance_config(effective_settings)
    risk_limits = limits or RiskLimits(
        max_position_oz=effective_settings.max_position_oz,
        stress_var_millions=effective_settings.stress_var_millions,
        daily_drawdown_pct=effective_settings.daily_drawdown_pct,
    )

    orders = _extract_orders(plan)
    violations: List[str] = []
    warnings: List[str] = []
    order_reports: List[Dict[str, Any]] = []

    net_exposure = 0.0

    for index, order in enumerate(orders):
        instrument = _normalise_token(order.get("instrument"))
        side = str(order.get("side", "")).strip().lower()
        counterparty = _normalise_token(order.get("counterparty"))
        size_raw = order.get("size_oz")
        size_oz: Optional[float] = None
        if isinstance(size_raw, (int, float)):
            size_oz = float(size_raw)
        elif isinstance(size_raw, str):
            cleaned = size_raw.strip()
            if cleaned:
                try:
                    size_oz = float(cleaned)
                except ValueError:
                    size_oz = None

        order_violations: List[str] = []
        order_warnings: List[str] = []

        if config.allowed_instruments and instrument and instrument not in config.allowed_instruments:
            order_violations.append("instrument_not_approved")
        if instrument and instrument in config.restricted_instruments:
            order_violations.append("instrument_restricted")

        if side not in {"buy", "sell"}:
            order_violations.append("invalid_side")

        if size_oz is None or size_oz <= 0:
            order_violations.append("invalid_size_oz")
        else:
            if size_oz > config.max_single_order_oz:
                order_violations.append("exceeds_single_order_limit")
            if size_oz > risk_limits.max_position_oz:
                order_violations.append("exceeds_position_limit")

        if config.require_stop_loss and not order.get("stop"):
            order_violations.append("missing_stop_loss")
        if config.require_take_profit and not order.get("target"):
            order_warnings.append("missing_take_profit")

        if config.allowed_counterparties and counterparty and counterparty not in config.allowed_counterparties:
            order_violations.append("counterparty_not_approved")
        if counterparty and counterparty in config.restricted_counterparties:
            order_violations.append("counterparty_restricted")

        if size_oz and side in {"buy", "sell"}:
            direction = 1.0 if side == "buy" else -1.0
            net_exposure += direction * size_oz

        report = {
            "index": index,
            "instrument": instrument or order.get("instrument"),
            "side": side,
            "size_oz": size_oz,
            "counterparty": counterparty or order.get("counterparty"),
            "violations": order_violations,
            "warnings": order_warnings,
        }
        order_reports.append(report)
        violations.extend(order_violations)
        warnings.extend(order_warnings)

    projected_position = current_position_oz + net_exposure
    position_limit = risk_limits.max_position_oz
    if position_limit and abs(projected_position) > position_limit + 1e-6:
        violations.append("projected_position_limit_breach")

    summary = {
        "orders_checked": len(orders),
        "net_exposure_oz": net_exposure,
        "projected_position_oz": projected_position,
        "position_limit_oz": position_limit,
        "violations": sorted(set(violations)),
        "warnings": sorted(set(warnings)),
        "order_reports": order_reports,
    }

    logger.debug(
        "Compliance evaluation complete (orders=%d, violations=%d, warnings=%d)",
        len(orders),
        len(summary["violations"]),
        len(summary["warnings"]),
    )
    return summary


__all__ = [
    "ComplianceConfig",
    "build_compliance_config",
    "evaluate_compliance",
]
