"""Basic smoke tests for market data services."""

from __future__ import annotations

import pytest

from autogentest1.services.market_data import fetch_price_history


@pytest.mark.skip(reason="External data source availability varies; provide integration setup before running.")
def test_fetch_price_history_smoke() -> None:
    history = fetch_price_history("XAUUSD", days=1)
    assert history is not None
