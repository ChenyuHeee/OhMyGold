"""Refresh cached news & sentiment data using configured APIs.

Run this script once or a few times per day (e.g. via cron):
`python scripts/refresh_news_cache.py`
"""

from __future__ import annotations

from pathlib import Path

from ohmygold.config.settings import get_settings
from ohmygold.services.news_ingest import collect_news_articles
from ohmygold.services.sentiment import collect_sentiment_snapshot


def main() -> None:
    settings = get_settings()
    symbol = settings.default_symbol

    articles = collect_news_articles(
        symbol,
        news_api_key=settings.news_api_key,
        alpha_vantage_api_key=settings.alpha_vantage_api_key,
        limit=50,
    )
    sentiment = collect_sentiment_snapshot(
        symbol,
        news_api_key=settings.news_api_key,
        alpha_vantage_api_key=settings.alpha_vantage_api_key,
    )

    print(f"Cached {len(articles)} articles for {symbol}.")
    print(
        "Latest sentiment score: "
        f"{sentiment['score']} (trend {sentiment['score_trend']}, "
        f"class {sentiment['classification']})"
    )
    cache_dir = Path(__file__).resolve().parents[1] / "src" / "ohmygold" / "outputs"
    print(f"Cache directory: {cache_dir}")


if __name__ == "__main__":
    main()
