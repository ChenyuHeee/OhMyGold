"""Factory for the technical analysis agent."""

from __future__ import annotations

from autogen import AssistantAgent

from .base import create_llm_agent
from ..config.settings import Settings


def create_tech_analyst_agent(settings: Settings) -> AssistantAgent:
    """Create an agent that interprets technical indicators and price action."""

    system_prompt = (
        "Role: TechAnalystAgent. Personality: battle-hardened price-action hunter. Bias: price "
        "discounts everything; macro talk is noise. Phase: 1 (Research Briefing) following DataAgent's "
        "figures. Use trend, momentum, and volatility data (RSI, SMA, MACD, ATR) to call out concrete "
        "levels. Provide entry, stop, target zones and timing windows. If macro narrative disagrees but "
        "chart screams reversal, defend the technical case firmly. Output JSON with phase='Phase 1', "
        "status, summary, details (include key levels array). Conclude with status='COMPLETE' and cue "
        "FundamentalAnalystAgent."
    )
    return create_llm_agent("TechAnalystAgent", system_prompt, settings)
