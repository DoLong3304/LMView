"""News scraper service for CryptoPanic API.

Fetches cryptocurrency news and prepares for sentiment analysis.
"""

import json
import logging
import os
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

# ── CryptoPanic API configuration ────────────────────────────────────────────
CRYPTOPANIC_API_KEY = os.environ.get("CRYPTOPANIC_API_KEY", "")
CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"
DEFAULT_CURRENCIES = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "MATIC", "DOT", "AVAX"]


class NewsScraperError(Exception):
    """Base exception for news scraper errors."""
    pass


class NewsScraper:
    """CryptoPanic news scraper.

    Usage::

        scraper = NewsScraper(api_key="YOUR_API_KEY")
        news_items = scraper.fetch_latest(currencies=["BTC", "ETH"], limit=20)
    """

    def __init__(self, api_key: str = None, max_retries: int = 3):
        self.api_key = api_key or CRYPTOPANIC_API_KEY
        self.max_retries = max_retries

        if not self.api_key:
            log.warning("CRYPTOPANIC_API_KEY not set. News scraping will be disabled.")

    def fetch_latest(
        self,
        currencies: list[str] = None,
        limit: int = 20,
        filter_type: str = "all",
    ) -> list[dict[str, Any]]:
        """Fetch latest news from CryptoPanic API.

        Args:
            currencies: List of currency symbols (e.g., ["BTC", "ETH"])
            limit: Maximum number of news items to fetch
            filter_type: Filter type ("all", "hot", "rising", "bullish", "bearish")

        Returns:
            List of news items with structure:
            {
                "id": int,
                "title": str,
                "url": str,
                "published_at": str (ISO 8601),
                "currencies": [{"code": "BTC", "title": "Bitcoin"}],
                "source": {"title": "CoinDesk", "domain": "coindesk.com"}
            }
        """
        if not self.api_key:
            log.warning("API key not configured. Returning empty news list.")
            return []

        currencies = currencies or DEFAULT_CURRENCIES
        currencies_param = ",".join(currencies)

        params = {
            "auth_token": self.api_key,
            "currencies": currencies_param,
            "filter": filter_type,
            "public": "true",
        }

        for attempt in range(self.max_retries):
            try:
                log.info(
                    "Fetching news from CryptoPanic (currencies=%s, filter=%s, attempt=%d)",
                    currencies_param,
                    filter_type,
                    attempt + 1,
                )

                resp = requests.get(CRYPTOPANIC_API_URL, params=params, timeout=15)

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    log.warning("Rate limited. Sleeping %ds...", retry_after)
                    time.sleep(retry_after)
                    continue

                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                log.info("Fetched %d news items from CryptoPanic.", len(results))

                # Limit results
                return results[:limit]

            except requests.exceptions.RequestException as e:
                log.warning("Fetch attempt %d failed: %s", attempt + 1, e)
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise NewsScraperError(f"Failed to fetch news after {self.max_retries} attempts") from e

        return []

    def extract_symbols(self, news_item: dict) -> list[str]:
        """Extract normalized symbol list from news item.

        Args:
            news_item: News item from CryptoPanic API

        Returns:
            List of symbols in canonical format (e.g., ["BTCUSDT", "ETHUSDT"])
        """
        currencies = news_item.get("currencies", [])
        symbols = []

        for currency in currencies:
            code = currency.get("code", "").upper()
            if code:
                # Convert BTC -> BTCUSDT
                symbol = f"{code}USDT"
                symbols.append(symbol)

        return symbols

    def format_for_kafka(
        self,
        news_item: dict,
        sentiment_score: float,
    ) -> dict[str, Any]:
        """Format news item for Kafka publishing.

        Args:
            news_item: Raw news item from CryptoPanic
            sentiment_score: Sentiment score from analyzer (-1.0 to 1.0)

        Returns:
            Formatted record matching news.avsc schema
        """
        # Parse published_at timestamp
        published_at_str = news_item.get("published_at", "")
        published_at_ms = None

        if published_at_str:
            try:
                # CryptoPanic uses ISO 8601 format: "2024-05-09T12:34:56Z"
                from datetime import datetime
                dt = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                published_at_ms = int(dt.timestamp() * 1000)
            except Exception as e:
                log.warning("Failed to parse published_at '%s': %s", published_at_str, e)

        source_info = news_item.get("source", {})
        source_title = source_info.get("title", "Unknown")

        return {
            "event_time": int(time.time() * 1000),
            "source": source_title,
            "title": news_item.get("title", ""),
            "sentiment_score": sentiment_score,
            "symbols": self.extract_symbols(news_item),
            "url": news_item.get("url"),
            "published_at": published_at_ms,
        }


def main():
    """Test scraper functionality."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    scraper = NewsScraper()
    news_items = scraper.fetch_latest(currencies=["BTC", "ETH"], limit=5)

    log.info("Fetched %d news items:", len(news_items))
    for item in news_items:
        log.info("  - %s", item.get("title", "")[:80])
        log.info("    Symbols: %s", scraper.extract_symbols(item))


if __name__ == "__main__":
    main()
