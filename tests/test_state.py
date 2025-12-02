"""Tests for portfolio state helpers."""

from __future__ import annotations

from pathlib import Path

from autogentest1.services import state


def _mock_state_path(tmp_path: Path) -> Path:
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir / "portfolio_state.json"


def test_load_state_returns_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(state, "_state_file_path", lambda: _mock_state_path(tmp_path))
    result = state.load_portfolio_state()
    assert result["positions"]["symbol"] == "XAUUSD"
    assert result["positions"]["net_oz"] == 0.0


def test_update_state_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(state, "_state_file_path", lambda: _mock_state_path(tmp_path))

    updated = state.update_portfolio_state({"positions": {"symbol": "XAUUSD", "net_oz": 100.0}})
    assert updated["positions"]["net_oz"] == 100.0
    saved = state.load_portfolio_state()
    assert saved["positions"]["net_oz"] == 100.0
