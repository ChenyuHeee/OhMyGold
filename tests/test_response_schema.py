"""Validation tests for agent JSON handoffs."""

from __future__ import annotations

from autogentest1.utils.response_validation import validate_workflow_response


def test_response_validation_allows_historical_references() -> None:
    payload = {
        "phase": "Phase 1",
        "status": "COMPLETE",
        "summary": "Macro context locked in",
        "details": {
            "next_agent": "TechAnalystAgent",
            "historical_references": [
                {"event": "Volcker tightening", "year": 1979, "takeaway": "Inflation spikes pulled gold higher."},
                {"event": "Pandemic liquidity rush", "year": 2020, "takeaway": "Initial sell-off followed by reflation rally."},
            ],
            "metrics": {
                "historical_var_99": -0.025,
                "scenario_outcomes": [
                    {"label": "minus_2pct", "projected_price": 1850.0},
                    {"label": "plus_2pct", "projected_price": 1940.0},
                ],
            },
        },
    }
    is_valid, error = validate_workflow_response(payload)
    assert is_valid, error


def test_response_validation_catches_missing_fields() -> None:
    payload = {
        "phase": "Phase 1",
        "status": "COMPLETE",
        "details": {},
    }
    is_valid, error = validate_workflow_response(payload)
    assert not is_valid
    assert "summary" in (error or "")
