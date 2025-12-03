"""Factory for the head trader agent overseeing the desk."""

from __future__ import annotations

from ..compat import AssistantAgent
from .base import create_llm_agent
from ..config.settings import Settings


def create_head_trader_agent(settings: Settings) -> AssistantAgent:
    """Create an agent that mirrors the head trader's responsibilities."""

    system_prompt = (
        "Role: HeadTraderAgent. Personality: calm, decisive portfolio captain balancing all viewpoints. "
        "Bias: maximize risk-adjusted outcomes while respecting guardrails and existing portfolio state. "
        "Phase: 2 (Trade Plan) plus any feedback cycles triggered by risk/compliance. Responsibilities: "
        "synthesize Phase 1 insights, consult the portfolio_state and feedback_rules, propose base and "
        "alternative strategies (size, entry, stop, hedge, contingency), and reopen discussions when "
        "RiskManagerAgent or ComplianceAgent reject a plan. Output JSON with phase ('Phase 2' or "
        "'Phase 2-REOPENED'), status, summary, details (include plan options, allocation rationale, "
        "next_steps array specifying the next agent). Maintain discipline: if risk rejects, adjust sizing "
        "or hedges before re-engaging PaperTraderAgent."
    )
    return create_llm_agent("HeadTraderAgent", system_prompt, settings)


def create_supervisor_agent(settings: Settings) -> AssistantAgent:
    """Backward compatible alias for the head trader agent."""

    return create_head_trader_agent(settings)
