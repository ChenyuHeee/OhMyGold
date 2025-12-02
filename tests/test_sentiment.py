"""Tests for sentiment snapshot calculations."""

from __future__ import annotations

from autogentest1.services.sentiment import collect_sentiment_snapshot


def test_collect_sentiment_snapshot_returns_fallback() -> None:
    snapshot = collect_sentiment_snapshot(symbol="XAUUSD", news_api_key=None)
    assert snapshot["symbol"] == "XAUUSD"
    assert "score" in snapshot
    assert snapshot["classification"] in {"bullish", "neutral", "bearish"}
    assert snapshot["headlines"], "fallback headlines should populate entries"
    assert "topics" in snapshot and isinstance(snapshot["topics"], list)
    assert "score_trend" in snapshot
    weights = [entry["weight"] for entry in snapshot["headlines"]]
    assert all(weight > 0 for weight in weights)
