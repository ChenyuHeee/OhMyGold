from types import SimpleNamespace

from ohmygold.workflows.gold_outlook import (
    _canonical_agent_name,
    _get_next_primary_after,
    _resolve_agent,
)


def test_canonical_aliases_map_to_expected_agents():
    assert _canonical_agent_name("QuantitativeAnalystAgent") == "QuantResearchAgent"
    assert _canonical_agent_name("TradingStrategyAgent") == "HeadTraderAgent"


def test_canonicalization_handles_case_and_spacing():
    assert _canonical_agent_name("headtraderagent") == "HeadTraderAgent"
    assert _canonical_agent_name("PaperTrader") == "PaperTraderAgent"


def test_canonicalization_is_idempotent_for_known_names():
    assert _canonical_agent_name("RiskManagerAgent") == "RiskManagerAgent"
    assert _canonical_agent_name(None) is None


def test_get_next_primary_after_uses_aliases():
    assert _get_next_primary_after("QuantitativeAnalystAgent") == "HeadTraderAgent"
    assert _get_next_primary_after("  riskmanager  ") == "ComplianceAgent"


def test_resolve_agent_matches_alias_names():
    agents = [
        SimpleNamespace(name="QuantResearchAgent"),
        SimpleNamespace(name="HeadTraderAgent"),
    ]
    resolved = _resolve_agent("QuantitativeAnalystAgent", agents)
    assert resolved is agents[0]
    assert _resolve_agent("TradingStrategyAgent", agents) is agents[1]
    assert _resolve_agent("UnknownAgent", agents) is None
