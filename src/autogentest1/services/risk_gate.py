"""Hard risk gate enforcement for trading plans.

This module inspects the final workflow payload alongside the
pre-computed risk snapshot and blocks execution when hard-coded
limits are breached. The checks are intentionally conservative so
that automated plans do not proceed when the desk would normally
escalate to humans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ..config.settings import Settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class HardRiskViolation:
    """Structured metadata describing a breached hard limit."""

    code: str
    message: str
    metric: Optional[float] = None
    limit: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.metric is not None:
            payload["metric"] = self.metric
        if self.limit is not None:
            payload["limit"] = self.limit
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(frozen=True)
class HardRiskGateReport:
    """Evaluation outcome for the hard gate layer."""

    violations: List[HardRiskViolation]
    evaluated_metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breached": self.breached,
            "violations": [violation.to_dict() for violation in self.violations],
            "evaluated_metrics": self.evaluated_metrics,
        }

    @property
    def breached(self) -> bool:
        return bool(self.violations)

    def summary(self) -> str:
        if not self.violations:
            return "No hard risk breaches detected."
        parts = [f"{violation.code}: {violation.message}" for violation in self.violations]
        return "; ".join(parts)


class HardRiskBreachError(RuntimeError):
    """Raised when the hard risk gate blocks the execution."""

    def __init__(self, report: HardRiskGateReport, *, result: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(report.summary())
        self.report = report
        self.partial_result = result

    def __str__(self) -> str:
        return f"Hard risk gate breached: {self.report.summary()}"


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip():
            return float(value)
    except (TypeError, ValueError):
        return None
    return None


def _largest_order_size(orders: Iterable[Mapping[str, Any]]) -> Optional[float]:
    sizes: List[float] = []
    for order in orders:
        size = order.get("size_oz") or order.get("size") or order.get("quantity")
        numeric = _safe_float(size)
        if numeric is not None:
            sizes.append(abs(numeric))
    return max(sizes) if sizes else None


def _has_stop_protection(orders: Iterable[Mapping[str, Any]]) -> bool:
    for order in orders:
        order_type = str(order.get("type", "")).upper()
        if order_type in {"STOP", "STOP_LIMIT", "STOP_LOSS"}:
            return True
        if _safe_float(order.get("stop")) is not None:
            return True
    return False


def _collect_orders(response: Mapping[str, Any]) -> List[Dict[str, Any]]:
    details = _as_dict(response.get("details"))
    execution = _as_dict(details.get("execution_checklist"))
    orders = execution.get("orders")
    if isinstance(orders, list):
        return [order for order in orders if isinstance(order, dict)]
    # fallback: some payloads surface orders directly under details
    direct_orders = details.get("orders")
    if isinstance(direct_orders, list):
        return [order for order in direct_orders if isinstance(order, dict)]
    return []


def _extract_risk_metrics(response: Mapping[str, Any]) -> Dict[str, Any]:
    details = _as_dict(response.get("details"))
    risk_compliance = _as_dict(details.get("risk_compliance_signoff"))
    metrics = _as_dict(risk_compliance.get("risk_metrics"))
    return metrics


def enforce_hard_limits(
    response: Mapping[str, Any],
    *,
    context: Mapping[str, Any],
    settings: Settings,
) -> HardRiskGateReport:
    """Evaluate the final workflow response against hard risk limits."""

    if not settings.hard_gate_enabled:
        return HardRiskGateReport(violations=[], evaluated_metrics={})

    violations: List[HardRiskViolation] = []
    evaluated: Dict[str, Any] = {}

    risk_snapshot = _as_dict(context.get("risk_snapshot"))
    risk_metrics = _extract_risk_metrics(response)
    orders = _collect_orders(response)

    # -- Position utilization -------------------------------------------------
    position_utilization = _safe_float(risk_metrics.get("position_utilization"))
    if position_utilization is None:
        position_utilization = _safe_float(risk_snapshot.get("position_utilization"))
    evaluated["position_utilization"] = position_utilization

    utilization_limit = settings.hard_gate_max_position_utilization
    if utilization_limit is None:
        utilization_limit = 1.0
    evaluated["position_utilization_limit"] = utilization_limit

    if (
        position_utilization is not None
        and utilization_limit is not None
        and position_utilization > utilization_limit
    ):
        violations.append(
            HardRiskViolation(
                code="POSITION_UTILIZATION",
                message="Proposed plan exceeds hard position utilization limit",
                metric=position_utilization,
                limit=utilization_limit,
            )
        )

    # -- Single order sizing --------------------------------------------------
    largest_order = _largest_order_size(orders)
    evaluated["largest_order_oz"] = largest_order

    single_order_limit = settings.hard_gate_max_single_order_oz
    if single_order_limit is None:
        single_order_limit = settings.compliance_max_single_order_oz or settings.max_position_oz
    evaluated["single_order_limit_oz"] = single_order_limit

    if (
        largest_order is not None
        and single_order_limit is not None
        and largest_order > single_order_limit
    ):
        violations.append(
            HardRiskViolation(
                code="SINGLE_ORDER_EXPOSURE",
                message="Largest ticket size exceeds hard limit",
                metric=largest_order,
                limit=single_order_limit,
            )
        )

    # -- Stop-loss coverage ---------------------------------------------------
    evaluated["has_stop_protection"] = _has_stop_protection(orders)
    if settings.hard_gate_require_stop_loss and not evaluated["has_stop_protection"]:
        violations.append(
            HardRiskViolation(
                code="STOP_LOSS_MISSING",
                message="No stop-loss protection detected for execution orders",
                details={"orders_checked": len(orders)},
            )
        )

    # -- Stress loss vs limit -------------------------------------------------
    stress_loss = _safe_float(risk_metrics.get("stress_test_worst_loss_millions"))
    evaluated["stress_test_worst_loss_millions"] = stress_loss

    stress_limit = settings.hard_gate_max_stress_loss_millions
    if stress_limit is None:
        stress_limit = settings.stress_var_millions
    evaluated["stress_loss_limit_millions"] = stress_limit

    if (
        stress_loss is not None
        and stress_limit is not None
        and stress_loss < 0
        and abs(stress_loss) > stress_limit
    ):
        violations.append(
            HardRiskViolation(
                code="STRESS_LOSS_LIMIT",
                message="Stress scenario loss exceeds configured maximum",
                metric=abs(stress_loss),
                limit=stress_limit,
            )
        )

    # -- Daily drawdown -------------------------------------------------------
    pnl_today = _safe_float(risk_snapshot.get("pnl_today_millions"))
    drawdown_floor = _safe_float(risk_snapshot.get("drawdown_threshold_millions"))
    evaluated["pnl_today_millions"] = pnl_today
    evaluated["drawdown_threshold_millions"] = drawdown_floor

    if (
        pnl_today is not None
        and drawdown_floor is not None
        and pnl_today <= drawdown_floor
    ):
        violations.append(
            HardRiskViolation(
                code="DAILY_DRAWDOWN",
                message="Daily PnL breaches drawdown floor",
                metric=pnl_today,
                limit=drawdown_floor,
            )
        )

    # -- Pre-computed risk alerts --------------------------------------------
    alerts = risk_snapshot.get("risk_alerts")
    fatal_alerts = {"position_limit_exceeded", "drawdown_limit_breached", "var_limit_exceeded", "scenario_loss_exceeds_limit"}
    if isinstance(alerts, list):
        blocking = [alert for alert in alerts if isinstance(alert, str) and alert in fatal_alerts]
        evaluated["blocking_alerts"] = blocking
        for alert in blocking:
            violations.append(
                HardRiskViolation(
                    code="RISK_ALERT",
                    message=f"Underlying risk snapshot flagged '{alert}'",
                )
            )
    else:
        evaluated["blocking_alerts"] = []

    # -- Cross-asset correlation ---------------------------------------------
    correlation_threshold = settings.hard_gate_correlation_threshold
    evaluated["correlation_threshold"] = correlation_threshold
    correlations = risk_snapshot.get("cross_asset_correlations")
    if isinstance(correlations, list) and correlation_threshold is not None:
        breached_pairs: List[Dict[str, Any]] = []
        for entry in correlations:
            if not isinstance(entry, Mapping):
                continue
            value = _safe_float(entry.get("value"))
            if value is None:
                continue
            if abs(value) >= correlation_threshold:
                breached_pairs.append(
                    {
                        "label": entry.get("label") or entry.get("symbol"),
                        "value": value,
                    }
                )
        evaluated["correlation_breaches"] = breached_pairs
        for pair in breached_pairs:
            violations.append(
                HardRiskViolation(
                    code="CORRELATION_LIMIT",
                    message=f"Correlation {pair['label']} {pair['value']:.2f} exceeds threshold {correlation_threshold:.2f}",
                    metric=pair["value"],
                    limit=correlation_threshold,
                )
            )
    else:
        evaluated["correlation_breaches"] = []

    if violations:
        for violation in violations:
            logger.error("硬风控约束触发：%s -> %s", violation.code, violation.message)

    return HardRiskGateReport(violations=violations, evaluated_metrics=evaluated)