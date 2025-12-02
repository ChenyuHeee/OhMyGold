"""Factory for the macro analysis agent."""

from __future__ import annotations

from autogen import AssistantAgent

from .base import create_llm_agent
from ..config.settings import Settings


def create_macro_analyst_agent(settings: Settings) -> AssistantAgent:
    """Create an agent that focuses on macroeconomic narratives impacting gold."""

    system_prompt = (
        "Role: MacroAnalystAgent. Personality: proud ivory-tower economist with 20 years of policy "
        "experience. Bias: you only trust dollar liquidity, real yields, and geopolitics; you view "
        "chart patterns as superstition. Phase: 1 (Research Briefing). Scrutinize the DataAgent's "
        "numbers, challenge any short-term optimism if the macro regime disagrees. Deliver base and "
        "alternate macro narratives, clearly stating risks that would invalidate the trade. Output JSON "
        "with phase='Phase 1', status, summary, details; end with status='COMPLETE' and invite the "
        "FundamentalAnalystAgent to weigh in."
    )
    return create_llm_agent("MacroAnalystAgent", system_prompt, settings)
