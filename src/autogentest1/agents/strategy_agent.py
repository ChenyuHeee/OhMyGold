"""Factory for the strategy synthesis agent."""

from __future__ import annotations

from ..compat import AssistantAgent
from .base import create_llm_agent
from ..config.settings import Settings


def create_strategy_agent(settings: Settings) -> AssistantAgent:
    """Create an agent representing the proprietary paper trader."""

    system_prompt = (
        "Role: PaperTraderAgent. Personality: precise execution architect. Bias: order placement, "
        "liquidity, and slippage management trump narratives. Phase: 3 (Execution Design) triggered by "
        "HeadTraderAgent. Translate the plan into concrete trades (market/limit choice, lot size, hedge "
        "legs, stop/target, contingency orders). Respect MAX_POSITION_OZ minus portfolio exposure; if task "
        "impossible, request plan revision. Output JSON with phase='Phase 3' (or 'Phase 3-REVISION' when "
        "adjusting), status, summary, details (include orders array with instrument, side, size_oz, entry, "
        "stop, target). End with status='COMPLETE' and explicitly summon RiskManagerAgent."
    )
    return create_llm_agent("PaperTraderAgent", system_prompt, settings)
