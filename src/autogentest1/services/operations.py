"""Operational checklists for settlement and logistics steps."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from ..utils.logging import get_logger

logger = get_logger(__name__)


def build_settlement_checklist(symbol: str) -> Dict[str, List[str]]:
    """Return end-of-day tasks for the settlement and logistics teams."""

    logger.info("Preparing settlement checklist for %s", symbol)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "date": today,
        "sections": [
            {
                "category": "cash_and_margin",
                "tasks": [
                    {
                        "description": "Reconcile futures margin with clearing broker",
                        "status": "pending",
                    },
                    {
                        "description": "Authorize cash movements for OTC counterparties",
                        "status": "pending",
                    },
                ],
            },
            {
                "category": "documentation",
                "tasks": [
                    {
                        "description": "Match trade confirmations against blotter",
                        "status": "pending",
                    },
                    {
                        "description": "Archive compliance-approved voice logs",
                        "status": "pending",
                    },
                ],
            },
            {
                "category": "logistics",
                "tasks": [
                    {
                        "description": "Confirm vault inventory levels",
                        "status": "pending",
                    },
                    {
                        "description": "Schedule transport for any spot deliveries",
                        "status": "pending",
                    },
                ],
            },
        ],
    }
