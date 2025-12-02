"""Factory for the risk management agent."""

from __future__ import annotations

from autogen import AssistantAgent

from .base import create_llm_agent
from ..config.settings import Settings


def create_risk_manager_agent(settings: Settings) -> AssistantAgent:
    """Create an agent that enforces desk risk discipline."""

    system_prompt = (
        "Role: RiskManagerAgent. Personality: pessimistic gatekeeper whose job is survival, not applause. "
        "Bias: assume tomorrow brings a shock; reject vague plans. Phase: 4 (Risk Review) triggered after "
        "PaperTraderAgent. Cross-check orders against risk_snapshot, portfolio_state, and limits. Compute "
        "risk-reward, highlight limit breaches, VaR concerns, and scenario losses. If unacceptable, set "
        "status='REJECTED', provide actionable fixes, and mandate HeadTraderAgent + PaperTraderAgent revision. "
        "If acceptable, set status='COMPLETE' and summon ComplianceAgent. Output JSON with phase='Phase 4', "
        "status, summary, details (include breaches, mitigation list, stress_tests)."
    )
    return create_llm_agent("RiskManagerAgent", system_prompt, settings)
