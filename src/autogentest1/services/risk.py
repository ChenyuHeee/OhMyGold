"""Risk monitoring utilities aligning with trading desk practices."""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Any, Dict, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskLimits:
    """Key risk guardrails supplied by configuration."""

    max_position_oz: float
    stress_var_millions: float
    daily_drawdown_pct: float


def build_risk_snapshot(
    symbol: str,
    history: Any,
    *,
    limits: RiskLimits,
    current_position_oz: float,
    pnl_today_millions: float,
) -> Dict[str, Any]:
    """Compute simple realized risk metrics for discussion."""

    from importlib import import_module

    try:  # pragma: no cover - optional dependency resolution
        np = import_module("numpy")
        import_module("pandas")
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ImportError(
            "The 'numpy' and 'pandas' packages are required for risk computations."
        ) from exc

    drawdown_threshold: Optional[float] = None
    if history.empty:
        logger.warning("Cannot compute risk snapshot without price history for %s", symbol)
        vol_annualized: Optional[float] = None
        drawdown_flag = False
    else:
        returns = history["Close"].astype(float).pct_change().dropna()
        vol_annualized = float(np.sqrt(252) * returns.std()) if not returns.empty else None
        drawdown_threshold = -limits.daily_drawdown_pct / 100 * limits.stress_var_millions
        drawdown_flag = pnl_today_millions <= drawdown_threshold

    utilization = (
        current_position_oz / limits.max_position_oz if limits.max_position_oz else None
    )

    if vol_annualized is not None and isinstance(vol_annualized, float) and isnan(vol_annualized):
        vol_annualized = None

    snapshot: Dict[str, Any] = {
        "current_position_oz": current_position_oz,
        "limit_position_oz": limits.max_position_oz,
        "position_utilization": utilization,
        "stress_var_limit_millions": limits.stress_var_millions,
        "pnl_today_millions": pnl_today_millions,
        "drawdown_alert": drawdown_flag,
        "drawdown_threshold_millions": drawdown_threshold,
        "realized_vol_annualized": vol_annualized,
    }
    return snapshot
