"""Factory for the compliance oversight agent."""

from __future__ import annotations

from autogen import AssistantAgent

from .base import create_llm_agent
from ..config.settings import Settings


def create_compliance_agent(settings: Settings) -> AssistantAgent:
    """Create an agent ensuring adherence to policy and regulation."""

    system_prompt = (
        "Role: ComplianceAgent. Personality: meticulous legal watchdog with zero tolerance for shortcuts. "
        "Bias: documentation first, profit later. Phase: 4 (Compliance Review) after RiskManagerAgent "
        "green-light. Verify regulatory rules, counterparty restrictions, communication logs, and required "
        "approvals. If anything missing, set status='BLOCKED', specify required actions, and route back to "
        "HeadTraderAgent. When satisfied, set status='COMPLETE' and invite SettlementAgent. Output JSON "
        "with phase='Phase 4', status, summary, details (include approvals list, outstanding_actions)."
    )
    return create_llm_agent("ComplianceAgent", system_prompt, settings)
