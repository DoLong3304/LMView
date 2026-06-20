"""
News fetcher with PostgreSQL persistence.
Fetches from multi-source scraper every 5 minutes and stores deduplicated articles.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.core.postgres import get_pg_pool
from src.news.enhanced_scraper import EnhancedMultiSourceScraper

logger = logging.getLogger(__name__)

TRACKED_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC",
    "LINK", "UNI", "ATOM", "LTC", "TRX", "NEAR", "APT", "SUI", "FIL", "ICP",
]

SYMBOL_PATTERNS = {
    symbol: re.compile(rf"\b{re.escape(symbol)}\b", re.IGNORECASE)
    for symbol in TRACKED_SYMBOLS
}


def _extract_symbols(title: str, summary: str, scraper_symbols: list[str] | None = None) -> list[str]:
    found = set(scraper_symbols or [])
    text = f"{title} {summary}".upper()
    for symbol, pattern in SYMBOL_PATTERNS.items():
        if pattern.search(text):
            found.add(symbol)
    return sorted(found)


def _normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    title = article.get("title", "") or ""
    summary = article.get("summary", "") or ""
    source = (article.get("source") or "unknown").strip().lower()
    url = article.get("url", "") or ""
    published_raw = article.get("published_at")
    if isinstance(published_raw, (int, float)):
        published_at = datetime.fromtimestamp(published_raw / 1000, tz=timezone.utc)
    elif isinstance(published_raw, str):
        try:
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        except Exception:
            published_at = datetime.now(timezone.utc)
    else:
        published_at = datetime.now(timezone.utc)

    symbols = _extract_symbols(title, summary, article.get("symbols") or [])

    return {
        "external_id": str(article.get("id") or url or title),
        "source": source,
        "title": title,
        "summary": summary[:1000] if summary else None,
        "url": url or None,
        "published_at": published_at,
        "fetched_at": datetime.now(timezone.utc),
        "symbols": symbols,
        "symbols_mentioned": symbols,
        "tags": article.get("tags") or [],
        "language": article.get("language") or "en",
        "content_snippet": (article.get("content") or summary or title)[:1500],
        "raw_payload": article,
        "raw_metadata": {
            "author": article.get("author"),
            "image_url": article.get("image_url"),
            "region": article.get("region"),
            "votes": article.get("votes") or {},
        },
    }


async def save_articles_to_postgres(articles: list[dict[str, Any]]) -> int:
    pool = await get_pg_pool()
    if pool is None:
        logger.warning("PostgreSQL pool unavailable; skipping news persistence")
        return 0

    inserted = 0
    async with pool.acquire() as conn:
        for article in articles:
            try:
                result = await conn.execute(
                    """
                    INSERT INTO news_articles (
                        external_id, source, title, summary, url, published_at, fetched_at,
                        symbols, symbols_mentioned, tags, language, content_snippet,
                        raw_payload, raw_metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::text[], $10::jsonb, $11, $12, $13::jsonb, $14::jsonb)
                    ON CONFLICT (source, external_id) WHERE external_id IS NOT NULL DO UPDATE
                    SET title = EXCLUDED.title,
                        summary = EXCLUDED.summary,
                        published_at = EXCLUDED.published_at,
                        fetched_at = EXCLUDED.fetched_at,
                        symbols = EXCLUDED.symbols,
                        symbols_mentioned = EXCLUDED.symbols_mentioned,
                        tags = EXCLUDED.tags,
                        language = EXCLUDED.language,
                        content_snippet = EXCLUDED.content_snippet,
                        raw_payload = EXCLUDED.raw_payload,
                        raw_metadata = EXCLUDED.raw_metadata
                    """,
                    article["external_id"],
                    article["source"],
                    article["title"],
                    article["summary"],
                    article["url"],
                    article["published_at"],
                    article["fetched_at"],
                    __import__("json").dumps(article["symbols"]),
                    article["symbols_mentioned"],
                    __import__("json").dumps(article["tags"]),
                    article["language"],
                    article["content_snippet"],
                    __import__("json").dumps(article["raw_payload"]),
                    __import__("json").dumps(article["raw_metadata"]),
                )
                if result == "INSERT 0 1":
                    inserted += 1
            except Exception as exc:
                logger.warning("Failed to persist article %s: %s", article.get("url") or article.get("title"), exc)
    return inserted


async def fetch_and_store_all_news() -> dict[str, Any]:
    scraper = EnhancedMultiSourceScraper(cryptopanic_api_key=None)
    fetched = await asyncio.to_thread(scraper.fetch_recent, 24, 10)
    normalized = [_normalize_article(article) for article in fetched]
    inserted = await save_articles_to_postgres(normalized)

    try:
        from backend.services.sentiment_service import batch_score_unscored_articles
        scored = await batch_score_unscored_articles(batch_size=20)
    except Exception as exc:
        logger.warning("Sentiment scoring after fetch failed: %s", exc)
        scored = 0

    logger.info("News fetch complete: fetched=%d inserted=%d scored=%d", len(normalized), inserted, scored)
    return {"fetched": len(normalized), "inserted": inserted, "scored": scored}


class NewsFetcherTask:
    def __init__(self, interval_seconds: int = 300):
        self.interval_seconds = interval_seconds
        self.task: asyncio.Task | None = None
        self.running = False

    async def start(self):
        if self.running:
            logger.warning("News fetcher already running")
            return
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("News fetcher task started (interval: %ds)", self.interval_seconds)

    async def stop(self):
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
        await asyncio.sleep(5)
        while self.running:
            try:
                await fetch_and_store_all_news()
            except Exception as exc:
                logger.error("Failed to fetch/store news: %s", exc, exc_info=True)
            await asyncio.sleep(self.interval_seconds)


news_fetcher = NewsFetcherTask(interval_seconds=300)
