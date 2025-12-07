"""Fundamental supply and demand insights for the gold market."""

from __future__ import annotations

from typing import Any, Dict

from ..utils.logging import get_logger

logger = get_logger(__name__)


def collect_fundamental_snapshot(symbol: str) -> Dict[str, Any]:
    """Return a structured snapshot of core fundamental drivers."""

    logger.info("整理基础面数据：%s", symbol)
    # Placeholder data; integrate real data providers such as World Gold Council in production.
    return {
        "central_bank_activity": {
            "trend": "net_buyer",
            "latest_month_tonnes": 35,
            "notable_buyers": ["PBOC", "RBI"],
        },
        "etf_flows": {
            "weekly_inflow_tonnes": -5.2,
            "year_to_date_change_tonnes": -18.4,
        },
        "physical_premium": {
            "region": "Asia",
            "currency": "USD/oz",
            "premium": 5.8,
        },
        "seasonal_demand": "jewellery_peak_season",
        "supply_notes": "Mines ramping up post-maintenance; recycling steady.",
    }
