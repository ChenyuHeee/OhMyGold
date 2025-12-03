"""Factory for the settlement and logistics agent."""

from __future__ import annotations

from ..compat import AssistantAgent
from .base import create_llm_agent
from ..config.settings import Settings


def create_settlement_agent(settings: Settings) -> AssistantAgent:
    """Create an agent responsible for operational closure tasks."""

    system_prompt = (
        "Role: SettlementAgent. Personality: disciplined back-office closer with a obsession for checklists. "
        "Bias: nothing counts unless reconciled. Phase: 5 (Operations Handoff) triggered by ComplianceAgent. "
        "Detail funding flows, margin calls, confirmations, logistics (vault/transport), and reconciliation. "
        "Use ToolsProxy functions (autogentest1.tools.portfolio.update_portfolio_state) to persist updated "
        "positions when Portfolio Update instructions are clear. Output JSON with phase='Phase 5', status, "
        "summary, details (tasks array with status, dependencies), plus portfolio_update if applied."
    )
    return create_llm_agent("SettlementAgent", system_prompt, settings)
