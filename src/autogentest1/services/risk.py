"""Risk monitoring utilities aligning with trading desk practices."""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

from ..utils.logging import get_logger
from .market_data import fetch_price_history
from .risk_math import ScenarioShock, apply_scenario, historical_var, rolling_correlation

if TYPE_CHECKING:  # pragma: no cover - type checker assistance only
    import pandas as pd

logger = get_logger(__name__)


@dataclass
class RiskLimits:
    """Key risk guardrails supplied by configuration."""

    max_position_oz: float
    stress_var_millions: float
    daily_drawdown_pct: float


@dataclass(frozen=True)
class CorrelationTarget:
    """Configure cross-asset correlation diagnostics."""

    symbol: str
    label: str
    window: int = 20


DEFAULT_CORRELATION_TARGETS: Sequence[CorrelationTarget] = (
    CorrelationTarget(symbol="DX-Y.NYB", label="US Dollar Index (DXY)", window=20),
    CorrelationTarget(symbol="^GSPC", label="S&P 500 Index", window=20),
    CorrelationTarget(symbol="TLT", label="Long-Term Treasuries ETF", window=20),
)


DEFAULT_SCENARIO_SHOCKS: Sequence[ScenarioShock] = (
    ScenarioShock(label="minus_2pct", pct_change=-0.02),
    ScenarioShock(label="minus_1pct", pct_change=-0.01),
    ScenarioShock(label="plus_1pct", pct_change=0.01),
    ScenarioShock(label="plus_2pct", pct_change=0.02),
)


def adjust_limits_with_news(
    limits: RiskLimits,
    news_snapshot: Mapping[str, Any],
    *,
    min_scale: float = 0.5,
    max_scale: float = 1.2,
) -> Tuple[RiskLimits, Dict[str, Any]]:
    """Scale risk limits based on headline-driven sentiment.

    The adjustment factors consider both the absolute news sentiment score and the
    confidence of that score. Higher confidence tightens limits, while a strongly
    bullish (bearish) bias can marginally expand (tighten) exposures within
    configured bounds.
    """

    score = float(news_snapshot.get("score", 0.0) or 0.0)
    confidence = float(news_snapshot.get("confidence", 0.0) or 0.0)
    classification = str(news_snapshot.get("classification", "neutral")).lower()
    trend = float(news_snapshot.get("score_trend", 0.0) or 0.0)

    confidence_clamped = max(0.0, min(2.0, confidence))
    score_clamped = max(-1.0, min(1.0, score))
    trend_clamped = max(-1.0, min(1.0, trend))

    directional_bias = 1.0 + (score_clamped + 0.3 * trend_clamped) * 0.25
    if classification == "bearish":
        directional_bias -= 0.1 * (abs(score_clamped) + 0.2 * confidence_clamped)
    elif classification == "bullish":
        directional_bias += 0.1 * max(0.0, score_clamped)

    tightening = 1.0 - 0.25 * confidence_clamped
    scale = max(min_scale, min(max_scale, directional_bias * tightening))

    adjusted = RiskLimits(
        max_position_oz=limits.max_position_oz * scale,
        stress_var_millions=limits.stress_var_millions * scale,
        daily_drawdown_pct=max(0.5, limits.daily_drawdown_pct * scale),
    )

    adjustment_meta = {
        "classification": classification,
        "score": score,
        "confidence": confidence,
        "trend": trend,
        "scale": scale,
    }

    return adjusted, adjustment_meta


def _fetch_benchmark_series(
    targets: Sequence[CorrelationTarget],
    *,
    lookback_days: int,
) -> Dict[str, "pd.Series"]:
    """Download benchmark closes for correlation diagnostics."""

    from importlib import import_module

    benchmark_series: Dict[str, "pd.Series"] = {}
    try:  # pragma: no cover - keep pandas optional
        pd = import_module("pandas")
    except ModuleNotFoundError:
        return benchmark_series

    for target in targets:
        try:
            history = fetch_price_history(target.symbol, days=lookback_days)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("基准行情下载失败：%s（%s）", target.symbol, exc)
            continue
        if history.empty:
            logger.debug("基准行情为空：%s", target.symbol)
            continue
        series = history.get("Close")
        if series is None or series.empty:
            logger.debug("基准缺少收盘价：%s", target.symbol)
            continue
        benchmark_series[target.symbol] = pd.Series(series.astype(float))
    return benchmark_series


def _compute_cross_asset_correlations(
    base_series: "pd.Series",
    benchmarks: Dict[str, "pd.Series"],
    *,
    targets: Sequence[CorrelationTarget],
) -> List[Dict[str, Any]]:
    """Calculate latest rolling correlation vs configured benchmarks."""

    from importlib import import_module
    import math

    diagnostics: List[Dict[str, Any]] = []
    if base_series.empty or not targets:
        return diagnostics

    try:  # pragma: no cover - keep pandas optional
        pd = import_module("pandas")
    except ModuleNotFoundError:
        return diagnostics

    base_series = pd.Series(base_series.astype(float)).dropna()
    if base_series.empty:
        return diagnostics

    for target in targets:
        peer = benchmarks.get(target.symbol)
        if peer is None:
            continue
        peer_series = pd.Series(peer.astype(float)).dropna()
        if peer_series.empty:
            continue

        aligned = pd.concat([base_series, peer_series], axis=1, join="inner").dropna()
        if aligned.empty:
            continue

        window = max(2, target.window)
        corr_series = rolling_correlation(aligned.iloc[:, 0], aligned.iloc[:, 1], window=window)
        latest = corr_series.dropna()
        value: Optional[float] = None
        if not latest.empty:
            value = float(latest.iloc[-1])
        else:
            tail = aligned.tail(window)
            if len(tail) == window:
                raw = float(tail.iloc[:, 0].corr(tail.iloc[:, 1]))
                value = None if math.isnan(raw) else raw

        if value is None:
            continue

        diagnostics.append(
            {
                "symbol": target.symbol,
                "label": target.label,
                "window": window,
                "value": value,
                "observations": int(len(aligned)),
            }
        )

    return diagnostics


def build_risk_snapshot(
    symbol: str,
    history: Any,
    *,
    limits: RiskLimits,
    current_position_oz: float,
    pnl_today_millions: float,
    benchmark_series: Optional[Dict[str, "pd.Series"]] = None,
    correlation_targets: Sequence[CorrelationTarget] = DEFAULT_CORRELATION_TARGETS,
    correlation_window: int = 20,
    scenario_shocks: Sequence[ScenarioShock] = DEFAULT_SCENARIO_SHOCKS,
    news_snapshot: Optional[Mapping[str, Any]] = None,
    apply_news_adjustment: bool = True,
) -> Dict[str, Any]:
    """Compute realized and hypothetical risk metrics for the desk."""

    from importlib import import_module

    try:  # pragma: no cover - optional dependency resolution
        np = import_module("numpy")
        pd = import_module("pandas")
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ImportError(
            "The 'numpy' and 'pandas' packages are required for risk computations."
        ) from exc

    close_series = pd.Series(dtype=float)
    latest_price: Optional[float] = None
    portfolio_var_millions: Optional[float] = None
    drawdown_threshold: Optional[float] = None
    effective_limits = limits
    news_adjustment: Optional[Dict[str, Any]] = None

    if apply_news_adjustment and news_snapshot:
        try:
            effective_limits, news_adjustment = adjust_limits_with_news(limits, news_snapshot)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("新闻驱动风险参数调节失败：%s", exc)
            effective_limits = limits

    if history.empty:
        logger.warning("缺少行情数据，无法计算风险快照：%s", symbol)
        vol_annualized: Optional[float] = None
        drawdown_flag = False
        var_99: Optional[float] = None
        scenario_outcomes: List[Dict[str, Any]] = []
        cross_asset_correlations: List[Dict[str, Any]] = []
    else:
        close_series = pd.Series(history["Close"].astype(float))
        latest_price = float(close_series.iloc[-1])
        returns = close_series.pct_change().dropna()
        vol_annualized = float(np.sqrt(252) * returns.std()) if not returns.empty else None
        drawdown_threshold = -effective_limits.daily_drawdown_pct / 100 * effective_limits.stress_var_millions
        drawdown_flag = pnl_today_millions <= drawdown_threshold
        var_value = historical_var(returns, confidence=0.99) if not returns.empty else float("nan")
        var_99 = None if np.isnan(var_value) else float(var_value)

        projections = apply_scenario(close_series, scenario_shocks)
        scenario_outcomes = []
        for label, value in projections:
            entry: Dict[str, Any] = {"label": label, "projected_price": value}
            if latest_price is not None:
                projected_pnl = (value - latest_price) * current_position_oz / 1_000_000
                entry["projected_pnl_millions"] = float(projected_pnl)
            scenario_outcomes.append(entry)

        if var_99 is not None and latest_price is not None:
            portfolio_var_millions = float(abs(var_99) * latest_price * current_position_oz / 1_000_000)

        if benchmark_series is None:
            lookback = max(len(close_series) + correlation_window, correlation_window * 3, 60)
            benchmark_series = _fetch_benchmark_series(correlation_targets, lookback_days=lookback)

        cross_asset_correlations = _compute_cross_asset_correlations(
            close_series,
            benchmark_series,
            targets=[
                CorrelationTarget(symbol=target.symbol, label=target.label, window=correlation_window)
                for target in correlation_targets
            ],
        )

    utilization = (
        current_position_oz / effective_limits.max_position_oz if effective_limits.max_position_oz else None
    )

    if vol_annualized is not None and isinstance(vol_annualized, float) and isnan(vol_annualized):
        vol_annualized = None

    var_limit_utilization: Optional[float] = None
    if portfolio_var_millions is not None and effective_limits.stress_var_millions:
        var_limit_utilization = portfolio_var_millions / effective_limits.stress_var_millions

    risk_alerts: List[str] = []
    if utilization is not None:
        if utilization > 1.0:
            risk_alerts.append("position_limit_exceeded")
        elif utilization >= 0.9:
            risk_alerts.append("position_limit_warning")

    if history.empty:
        drawdown_flag = False

    if drawdown_flag:
        risk_alerts.append("drawdown_limit_breached")

    if var_limit_utilization is not None:
        if var_limit_utilization > 1.0:
            risk_alerts.append("var_limit_exceeded")
        elif var_limit_utilization >= 0.8:
            risk_alerts.append("var_limit_warning")

    for outcome in scenario_outcomes:
        projected = outcome.get("projected_pnl_millions")
        if projected is not None and projected < -effective_limits.stress_var_millions:
            risk_alerts.append("scenario_loss_exceeds_limit")
            break

    snapshot: Dict[str, Any] = {
        "symbol": symbol,
        "current_position_oz": current_position_oz,
        "limit_position_oz": effective_limits.max_position_oz,
        "position_utilization": utilization,
        "stress_var_limit_millions": effective_limits.stress_var_millions,
        "pnl_today_millions": pnl_today_millions,
        "drawdown_alert": drawdown_flag,
        "drawdown_threshold_millions": drawdown_threshold,
        "realized_vol_annualized": vol_annualized,
        "historical_var_99": var_99,
        "portfolio_var_millions": portfolio_var_millions,
        "var_limit_utilization": var_limit_utilization,
        "scenario_outcomes": scenario_outcomes,
        "cross_asset_correlations": cross_asset_correlations,
        "risk_alerts": risk_alerts,
        "latest_price": latest_price,
        "base_limits": {
            "max_position_oz": limits.max_position_oz,
            "stress_var_millions": limits.stress_var_millions,
            "daily_drawdown_pct": limits.daily_drawdown_pct,
        },
        "adjusted_limits": {
            "max_position_oz": effective_limits.max_position_oz,
            "stress_var_millions": effective_limits.stress_var_millions,
            "daily_drawdown_pct": effective_limits.daily_drawdown_pct,
        },
        "news_adjustment": news_adjustment,
    }
    return snapshot
