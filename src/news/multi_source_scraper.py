"""
Multi-Source News Scraper
Fetches crypto news from 10+ major sources worldwide
"""
import requests
import feedparser
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)


class NewsSource:
    """Base class for news sources"""

    def __init__(self, name: str, url: str, source_type: str = "rss"):
        self.name = name
        self.url = url
        self.source_type = source_type

    def fetch(self) -> List[Dict]:
        """Fetch news from source"""
        raise NotImplementedError


class RSSNewsSource(NewsSource):
    """RSS feed news source"""

    def fetch(self, limit: int = 20) -> List[Dict]:
        """Fetch news from RSS feed"""
        try:
            feed = feedparser.parse(self.url)
            articles = []

            for entry in feed.entries[:limit]:
                article = {
                    "source": self.name,
                    "title": entry.get("title", ""),
                    "content": entry.get("summary", entry.get("description", "")),
                    "url": entry.get("link", ""),
                    "author": entry.get("author", "Unknown"),
                    "published_at": self._parse_date(entry.get("published", "")),
                    "symbols": []  # Will be extracted later
                }
                articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from {self.name}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching from {self.name}: {e}")
            return []

    def _parse_date(self, date_str: str) -> int:
        """Parse date string to Unix timestamp"""
        try:
            if date_str:
                dt = feedparser._parse_date(date_str)
                if dt:
                    return int(datetime(*dt[:6]).timestamp() * 1000)
        except:
            pass
        return int(datetime.now().timestamp() * 1000)


class APINewsSource(NewsSource):
    """API-based news source"""

    def __init__(self, name: str, url: str, api_key: Optional[str] = None):
        super().__init__(name, url, "api")
        self.api_key = api_key

    def fetch(self, limit: int = 20) -> List[Dict]:
        """Fetch news from API"""
        raise NotImplementedError


class CryptoPanicSource(APINewsSource):
    """CryptoPanic API source"""

    def fetch(self, limit: int = 20) -> List[Dict]:
        """Fetch from CryptoPanic API"""
        try:
            params = {
                "auth_token": self.api_key,
                "public": "true",
                "kind": "news",
                "filter": "hot"
            }

            response = requests.get(self.url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data.get("results", [])[:limit]:
                article = {
                    "source": self.name,
                    "title": item.get("title", ""),
                    "content": item.get("title", ""),  # CryptoPanic doesn't provide full content
                    "url": item.get("url", ""),
                    "author": item.get("source", {}).get("title", "Unknown"),
                    "published_at": self._parse_date(item.get("published_at", "")),
                    "symbols": [c["code"] for c in item.get("currencies", [])]
                }
                articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from {self.name}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching from {self.name}: {e}")
            return []

    def _parse_date(self, date_str: str) -> int:
        """Parse ISO date to Unix timestamp"""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except:
            return int(datetime.now().timestamp() * 1000)


class MultiSourceNewsScraper:
    """
    Scrapes news from 10+ major crypto news sources
    """

    def __init__(self, cryptopanic_api_key: Optional[str] = None):
        self.sources = self._initialize_sources(cryptopanic_api_key)

    def _initialize_sources(self, cryptopanic_api_key: Optional[str]) -> List[NewsSource]:
        """Initialize all news sources"""
        sources = []

        # 1. CryptoPanic (API)
        if cryptopanic_api_key:
            sources.append(CryptoPanicSource(
                name="CryptoPanic",
                url="https://cryptopanic.com/api/v1/posts/",
                api_key=cryptopanic_api_key
            ))

        # 2. CoinDesk (RSS)
        sources.append(RSSNewsSource(
            name="CoinDesk",
            url="https://www.coindesk.com/arc/outboundfeeds/rss/"
        ))

        # 3. CoinTelegraph (RSS)
        sources.append(RSSNewsSource(
            name="CoinTelegraph",
            url="https://cointelegraph.com/rss"
        ))

        # 4. Decrypt (RSS)
        sources.append(RSSNewsSource(
            name="Decrypt",
            url="https://decrypt.co/feed"
        ))

        # 5. The Block (RSS)
        sources.append(RSSNewsSource(
            name="The Block",
            url="https://www.theblock.co/rss.xml"
        ))

        # 6. Bitcoin Magazine (RSS)
        sources.append(RSSNewsSource(
            name="Bitcoin Magazine",
            url="https://bitcoinmagazine.com/.rss/full/"
        ))

        # 7. CryptoSlate (RSS)
        sources.append(RSSNewsSource(
            name="CryptoSlate",
            url="https://cryptoslate.com/feed/"
        ))

        # 8. BeInCrypto (RSS)
        sources.append(RSSNewsSource(
            name="BeInCrypto",
            url="https://beincrypto.com/feed/"
        ))

        # 9. NewsBTC (RSS)
        sources.append(RSSNewsSource(
            name="NewsBTC",
            url="https://www.newsbtc.com/feed/"
        ))

        # 10. U.Today (RSS)
        sources.append(RSSNewsSource(
            name="U.Today",
            url="https://u.today/rss"
        ))

        # 11. Bitcoinist (RSS)
        sources.append(RSSNewsSource(
            name="Bitcoinist",
            url="https://bitcoinist.com/feed/"
        ))

        # 12. CryptoNews (RSS)
        sources.append(RSSNewsSource(
            name="CryptoNews",
            url="https://cryptonews.com/news/feed/"
        ))

        logger.info(f"Initialized {len(sources)} news sources")
        return sources

    def fetch_all(self, articles_per_source: int = 10) -> List[Dict]:
        """
        Fetch news from all sources

        Args:
            articles_per_source: Number of articles to fetch per source

        Returns:
            List of articles from all sources
        """
        all_articles = []

        for source in self.sources:
            try:
                articles = source.fetch(limit=articles_per_source)
                all_articles.extend(articles)

                # Rate limiting - be nice to servers
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                continue

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                unique_articles.append(article)

        logger.info(f"Fetched {len(unique_articles)} unique articles from {len(self.sources)} sources")
        return unique_articles

    def fetch_recent(self, hours: int = 24, articles_per_source: int = 20) -> List[Dict]:
        """
        Fetch recent news from last N hours

        Args:
            hours: Number of hours to look back
            articles_per_source: Number of articles to fetch per source

        Returns:
            List of recent articles
        """
        all_articles = self.fetch_all(articles_per_source)

        # Filter by time
        cutoff_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
        recent_articles = [a for a in all_articles if a["published_at"] >= cutoff_time]

        # Sort by published date (newest first)
        recent_articles.sort(key=lambda x: x["published_at"], reverse=True)

        logger.info(f"Found {len(recent_articles)} articles from last {hours} hours")
        return recent_articles


# Example usage
if __name__ == "__main__":
    import os

    # Initialize scraper
    api_key = os.getenv("CRYPTOPANIC_API_KEY")
    scraper = MultiSourceNewsScraper(cryptopanic_api_key=api_key)

    # Fetch recent news
    articles = scraper.fetch_recent(hours=24, articles_per_source=10)

    print(f"Fetched {len(articles)} articles")
    for article in articles[:5]:
        print(f"- [{article['source']}] {article['title']}")
