"""Portfolio persistence helpers accessible via ToolProxy."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from ..services.state import load_portfolio_state, save_portfolio_state


def get_portfolio_state() -> Dict[str, Any]:
    """Return the current portfolio state."""

    return load_portfolio_state()


def update_portfolio_state(update: Dict[str, Any]) -> Dict[str, Any]:
    """Merge the provided update into the existing portfolio state and save it."""

    state = load_portfolio_state()
    state.update(update)
    state["last_updated"] = datetime.utcnow().isoformat()
    save_portfolio_state(state)
    return state
