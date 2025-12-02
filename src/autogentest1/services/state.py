"""Persistent portfolio state helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..utils.logging import get_logger

logger = get_logger(__name__)

_STATE_FILENAME = "portfolio_state.json"


def _state_file_path() -> Path:
    return Path(__file__).resolve().parent.parent / "outputs" / _STATE_FILENAME


def load_portfolio_state() -> Dict[str, Any]:
    """Load portfolio state from disk or return defaults."""

    path = _state_file_path()
    if not path.exists():
        logger.info("未找到状态文件：%s，使用默认参数", path)
        return {
            "positions": {
                "symbol": "XAUUSD",
                "net_oz": 0.0,
                "average_cost": None,
            },
            "pnl": {
                "realized_millions": 0.0,
                "unrealized_millions": 0.0,
            },
            "last_updated": None,
        }

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        logger.error("状态文件解析失败 %s：%s", path, exc)
        return {
            "positions": {
                "symbol": "XAUUSD",
                "net_oz": 0.0,
                "average_cost": None,
            },
            "pnl": {
                "realized_millions": 0.0,
                "unrealized_millions": 0.0,
            },
            "last_updated": None,
        }


def save_portfolio_state(state: Dict[str, Any]) -> Path:
    """Persist the portfolio state to disk."""

    path = _state_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    logger.info("组合状态已保存：%s", path)
    return path


def update_portfolio_state(update: Dict[str, Any]) -> Dict[str, Any]:
    """Merge partial updates into the stored portfolio state and persist."""

    state = load_portfolio_state()
    state.update(update)
    save_portfolio_state(state)
    return state