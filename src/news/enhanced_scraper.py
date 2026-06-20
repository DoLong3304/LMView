"""
Enhanced News Scraper with 12+ sources
Continuous updates every 5 minutes
"""
import requests
import feedparser
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import time
import hashlib
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class EnhancedNewsSource:
    """Enhanced news source with metadata"""

    def __init__(
        self,
        name: str,
        url: str,
        source_type: str = "rss",
        api_key: Optional[str] = None,
        language: str = "en",
        region: str = "global"
    ):
        self.name = name
        self.url = url
        self.source_type = source_type
        self.api_key = api_key
        self.language = language
        self.region = region
        self.last_fetch = None
        self.fetch_count = 0
        self.error_count = 0

    def fetch(self, limit: int = 20) -> List[Dict]:
        """Fetch news from source"""
        raise NotImplementedError

    def _generate_id(self, url: str, title: str) -> str:
        """Generate unique ID for article"""
        content = f"{url}:{title}"
        return hashlib.md5(content.encode()).hexdigest()


class EnhancedRSSSource(EnhancedNewsSource):
    """Enhanced RSS feed source with full content extraction"""

    def fetch(self, limit: int = 20) -> List[Dict]:
        """Fetch news from RSS feed"""
        try:
            feed = feedparser.parse(self.url)
            articles = []

            for entry in feed.entries[:limit]:
                # Extract full content if available
                content = self._extract_content(entry)

                # Extract image
                image_url = self._extract_image(entry)

                # Extract tags/categories
                tags = self._extract_tags(entry)

                article = {
                    "id": self._generate_id(entry.get("link", ""), entry.get("title", "")),
                    "source": self.name,
                    "title": entry.get("title", ""),
                    "content": content,
                    "summary": entry.get("summary", entry.get("description", ""))[:500],
                    "url": entry.get("link", ""),
                    "author": entry.get("author", "Unknown"),
                    "published_at": self._parse_date(entry.get("published", "")),
                    "image_url": image_url,
                    "tags": tags,
                    "symbols": [],  # Will be extracted later
                    "language": self.language,
                    "region": self.region
                }
                articles.append(article)

            self.last_fetch = datetime.now()
            self.fetch_count += 1
            logger.info(f"✅ {self.name}: Fetched {len(articles)} articles")
            return articles

        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ {self.name}: Error - {e}", exc_info=True)
            return []

    def _extract_content(self, entry) -> str:
        """Extract full content from entry"""
        # Try content field first
        if hasattr(entry, 'content'):
            return entry.content[0].value if entry.content else ""

        # Try description
        if hasattr(entry, 'description'):
            return entry.description

        # Try summary
        if hasattr(entry, 'summary'):
            return entry.summary

        return ""

    def _extract_image(self, entry) -> Optional[str]:
        """Extract image URL from entry"""
        # Try media:thumbnail
        if hasattr(entry, 'media_thumbnail'):
            return entry.media_thumbnail[0]['url'] if entry.media_thumbnail else None

        # Try media:content
        if hasattr(entry, 'media_content'):
            return entry.media_content[0]['url'] if entry.media_content else None

        # Try enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'image' in enclosure.get('type', ''):
                    return enclosure.get('href')

        # Try to extract from content
        if hasattr(entry, 'summary'):
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']

        return None

    def _extract_tags(self, entry) -> List[str]:
        """Extract tags/categories from entry"""
        tags = []

        if hasattr(entry, 'tags'):
            tags.extend([tag.term for tag in entry.tags])

        if hasattr(entry, 'categories'):
            tags.extend([cat for cat in entry.categories])

        return list(set(tags))[:5]  # Max 5 tags

    def _parse_date(self, date_str: str) -> int:
        """Parse date string to Unix timestamp (milliseconds).
        """
        import email.utils
        from datetime import datetime, timezone
        try:
            if date_str:
                dt = email.utils.parsedate_to_datetime(date_str)
                return int(dt.timestamp() * 1000)
        except Exception as exc:
            # Try to parse ISO format if email.utils fails
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            except Exception:
                logger.debug("unparseable date %r: %s", date_str, exc)
        return int(datetime.now().timestamp() * 1000)


class EnhancedCryptoPanicSource(EnhancedNewsSource):
    """Enhanced CryptoPanic API source"""

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
                    "id": str(item.get("id", "")),
                    "source": self.name,
                    "title": item.get("title", ""),
                    "content": item.get("title", ""),
                    "summary": item.get("title", "")[:500],
                    "url": item.get("url", ""),
                    "author": item.get("source", {}).get("title", "Unknown"),
                    "published_at": self._parse_date(item.get("published_at", "")),
                    "image_url": None,
                    "tags": [v.get("title", "") for v in item.get("votes", {}).values() if isinstance(v, dict)],
                    "symbols": [c["code"] for c in item.get("currencies", [])],
                    "language": self.language,
                    "region": self.region,
                    "votes": item.get("votes", {})
                }
                articles.append(article)

            self.last_fetch = datetime.now()
            self.fetch_count += 1
            logger.info(f"✅ {self.name}: Fetched {len(articles)} articles")
            return articles

        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ {self.name}: Error - {e}")
            return []

    def _parse_date(self, date_str: str) -> int:
        """Parse ISO date to Unix timestamp"""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except:
            return int(datetime.now().timestamp() * 1000)


class EnhancedMultiSourceScraper:
    """
    Enhanced scraper with 12+ sources
    Features:
    - Full content extraction
    - Image extraction
    - Tags/categories
    - Deduplication
    - Error tracking
    - Source health monitoring
    """

    def __init__(self, cryptopanic_api_key: Optional[str] = None):
        self.sources = self._initialize_sources(cryptopanic_api_key)
        self.cache = {}  # URL -> article cache
        self.stats = {
            "total_fetched": 0,
            "total_errors": 0,
            "last_update": None
        }

    def _initialize_sources(self, cryptopanic_api_key: Optional[str]) -> List[EnhancedNewsSource]:
        """Initialize all 12+ news sources"""
        sources = []

        # 1. CryptoPanic (API) - Aggregated news
        if cryptopanic_api_key:
            sources.append(EnhancedCryptoPanicSource(
                name="CryptoPanic",
                url="https://cryptopanic.com/api/v1/posts/",
                source_type="api",
                api_key=cryptopanic_api_key,
                language="en",
                region="global"
            ))

        # 2. CoinDesk - Leading crypto news
        sources.append(EnhancedRSSSource(
            name="CoinDesk",
            url="https://www.coindesk.com/arc/outboundfeeds/rss/",
            language="en",
            region="global"
        ))

        # 3. CoinTelegraph - Major publication
        sources.append(EnhancedRSSSource(
            name="CoinTelegraph",
            url="https://cointelegraph.com/rss",
            language="en",
            region="global"
        ))

        # 4. Decrypt - Blockchain news
        sources.append(EnhancedRSSSource(
            name="Decrypt",
            url="https://decrypt.co/feed",
            language="en",
            region="global"
        ))

        # 5. The Block - Research & news
        sources.append(EnhancedRSSSource(
            name="The Block",
            url="https://www.theblock.co/rss.xml",
            language="en",
            region="global"
        ))

        # 6. Bitcoin Magazine - Bitcoin-focused
        sources.append(EnhancedRSSSource(
            name="Bitcoin Magazine",
            url="https://bitcoinmagazine.com/.rss/full/",
            language="en",
            region="global"
        ))

        # 7. CryptoSlate - News & data
        sources.append(EnhancedRSSSource(
            name="CryptoSlate",
            url="https://cryptoslate.com/feed/",
            language="en",
            region="global"
        ))

        # 8. BeInCrypto - Global news
        sources.append(EnhancedRSSSource(
            name="BeInCrypto",
            url="https://beincrypto.com/feed/",
            language="en",
            region="global"
        ))

        # 9. NewsBTC - Bitcoin news
        sources.append(EnhancedRSSSource(
            name="NewsBTC",
            url="https://www.newsbtc.com/feed/",
            language="en",
            region="global"
        ))

        # 10. U.Today - Fintech news
        sources.append(EnhancedRSSSource(
            name="U.Today",
            url="https://u.today/rss",
            language="en",
            region="global"
        ))

        # 11. Bitcoinist - Bitcoin news
        sources.append(EnhancedRSSSource(
            name="Bitcoinist",
            url="https://bitcoinist.com/feed/",
            language="en",
            region="global"
        ))

        # 12. CryptoNews - News portal
        sources.append(EnhancedRSSSource(
            name="CryptoNews",
            url="https://cryptonews.com/news/feed/",
            language="en",
            region="global"
        ))

        logger.info(f"📰 Initialized {len(sources)} news sources")
        return sources

    def fetch_all(self, articles_per_source: int = 10) -> List[Dict]:
        """
        Fetch news from all sources with deduplication

        Returns:
            List of unique articles with full metadata
        """
        all_articles = []

        for source in self.sources:
            try:
                articles = source.fetch(limit=articles_per_source)
                all_articles.extend(articles)

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                continue

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []

        for article in all_articles:
            url = article["url"]
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        # Sort by published date (newest first)
        unique_articles.sort(key=lambda x: x["published_at"], reverse=True)

        # Update stats
        self.stats["total_fetched"] += len(unique_articles)
        self.stats["last_update"] = datetime.now()

        logger.info(f"📊 Fetched {len(unique_articles)} unique articles from {len(self.sources)} sources")
        return unique_articles

    def fetch_recent(self, hours: int = 24, articles_per_source: int = 20) -> List[Dict]:
        """Fetch recent news from last N hours"""
        all_articles = self.fetch_all(articles_per_source)

        # Filter by time
        cutoff_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
        recent_articles = [a for a in all_articles if a["published_at"] >= cutoff_time]

        logger.info(f"📅 Found {len(recent_articles)} articles from last {hours} hours")
        return recent_articles

    def get_source_health(self) -> Dict:
        """Get health status of all sources"""
        health = {
            "total_sources": len(self.sources),
            "healthy_sources": 0,
            "unhealthy_sources": 0,
            "sources": []
        }

        for source in self.sources:
            status = {
                "name": source.name,
                "type": source.source_type,
                "fetch_count": source.fetch_count,
                "error_count": source.error_count,
                "last_fetch": source.last_fetch.isoformat() if source.last_fetch else None,
                "health": "healthy" if source.error_count < 3 else "unhealthy"
            }

            if status["health"] == "healthy":
                health["healthy_sources"] += 1
            else:
                health["unhealthy_sources"] += 1

            health["sources"].append(status)

        return health


# Example usage
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)

    api_key = os.getenv("CRYPTOPANIC_API_KEY")
    scraper = EnhancedMultiSourceScraper(cryptopanic_api_key=api_key)

    # Fetch recent news
    articles = scraper.fetch_recent(hours=1, articles_per_source=5)

    print(f"\n📰 Fetched {len(articles)} articles:\n")
    for article in articles[:10]:
        print(f"[{article['source']}] {article['title']}")
        print(f"   URL: {article['url']}")
        print(f"   Published: {datetime.fromtimestamp(article['published_at']/1000)}")
        print()

    # Check source health
    health = scraper.get_source_health()
    print(f"\n🏥 Source Health: {health['healthy_sources']}/{health['total_sources']} healthy")
