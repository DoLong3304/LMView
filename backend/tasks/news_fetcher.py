"""
Background task to fetch news from multiple sources.
Runs every 5 minutes to keep news cache fresh.
"""
import asyncio
import logging
import os
from datetime import datetime

from src.news.enhanced_scraper import EnhancedMultiSourceScraper
from src.news.sentiment_analyzer import SentimentAnalyzer
from backend.services import news_service

logger = logging.getLogger(__name__)


class NewsFetcherTask:
    """Background task to fetch and cache news articles."""

    def __init__(self, interval_seconds: int = 300):
        self.interval_seconds = interval_seconds
        self.scraper = None
        self.sentiment_analyzer = None
        self.task = None
        self.running = False

    async def start(self):
        """Start the background task."""
        if self.running:
            logger.warning("News fetcher already running")
            return

        # Initialize scraper and sentiment analyzer
        api_key = os.getenv("CRYPTOPANIC_API_KEY")
        self.scraper = EnhancedMultiSourceScraper(cryptopanic_api_key=api_key)
        self.sentiment_analyzer = SentimentAnalyzer()

        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("News fetcher task started (interval: %ds)", self.interval_seconds)

    async def stop(self):
        """Stop the background task."""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("News fetcher task stopped")

    async def _run(self):
        """Main loop to fetch news periodically."""
        # Delay first fetch to avoid blocking startup
        await asyncio.sleep(5)
        await self._fetch_and_cache()

        while self.running:
            try:
                await asyncio.sleep(self.interval_seconds)
                if self.running:
                    await self._fetch_and_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in news fetcher loop: %s", e, exc_info=True)
                await asyncio.sleep(60)  # Wait 1 min before retry

    async def _fetch_and_cache(self):
        """Fetch news from all sources and update cache."""
        try:
            logger.info("Fetching news from all sources...")
            start_time = datetime.now()

            # Fetch in thread pool (blocking I/O)
            articles = await asyncio.to_thread(
                self.scraper.fetch_recent,
                hours=24,
                articles_per_source=10
            )

            # Add sentiment scores
            for article in articles:
                text = f"{article.get('title', '')} {article.get('summary', '')}"
                sentiment_score = self.sentiment_analyzer.analyze(text)
                article["sentiment_score"] = sentiment_score
                article["sentiment_label"] = self.sentiment_analyzer.classify(sentiment_score)

            # Update cache
            news_service.update_news_cache(articles)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                "✅ Fetched %d articles in %.2fs (sentiment analyzed)",
                len(articles),
                elapsed
            )

        except Exception as e:
            logger.error("Failed to fetch news: %s", e, exc_info=True)


# Global instance
news_fetcher = NewsFetcherTask(interval_seconds=300)  # 5 minutes
