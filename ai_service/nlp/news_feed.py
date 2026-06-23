"""RSS news feed ingester for LMView.

Fetches articles from major crypto news RSS feeds and stores them
in the ``news_articles`` PostgreSQL table for downstream FinBERT
sentiment analysis.

Designed to run as a background periodic task (every 15 minutes).
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from feedparser import parse as feed_parse

from backend.core.postgres import get_pg_pool

logger = logging.getLogger("ai_service.nlp.news_feed")

# Crypto news RSS feeds with reliability ratings
NEWS_FEEDS: List[Dict[str, Any]] = [
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "reliability": 0.9},
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss", "reliability": 0.85},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "reliability": 0.8},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "reliability": 0.85},
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/feed", "reliability": 0.8},
]


async def fetch_and_store_feeds() -> Dict[str, int]:
    """Fetch all RSS feeds and store new articles into ``news_articles``.

    Returns a dict with counts of new articles found per source.
    """
    pool = await get_pg_pool()
    if pool is None:
        logger.warning("Database unavailable — cannot store news articles")
        return {}

    counts: Dict[str, int] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for feed in NEWS_FEEDS:
            name = feed["name"]
            url = feed["url"]
            reliability = feed.get("reliability", 0.5)

            try:
                resp = await client.get(url)
                resp.raise_for_status()
                parsed = feed_parse(resp.text)
            except Exception as exc:
                logger.warning("Failed to fetch RSS feed %s: %s", name, exc)
                continue

            new_count = 0
            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                summary = entry.get("summary", "").strip()[:5000]

                if not title or not link:
                    continue

                # Convert published_parsed to datetime
                pub_dt = None
                if published:
                    try:
                        pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                if pub_dt is None:
                    pub_dt = datetime.now(timezone.utc)

                # Deduplicate by URL (link)
                async with pool.acquire() as conn:
                    existing = await conn.fetchval(
                        "SELECT id FROM news_articles WHERE url = $1 AND source = $2",
                        link, name,
                    )
                    if existing:
                        continue

                    # Insert article
                    await conn.execute(
                        """
                        INSERT INTO news_articles
                            (title, source, url, summary, published_at, fetched_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        title,
                        name,
                        link,
                        summary[:5000],
                        pub_dt,
                        datetime.now(timezone.utc),
                    )
                    new_count += 1

            counts[name] = new_count
            if new_count > 0:
                logger.info("Fetched %d new articles from %s", new_count, name)

    return counts


async def news_feed_loop(interval_seconds: int = 900) -> None:
    """Background loop: fetch RSS feeds every *interval_seconds*."""
    logger.info("Starting news feed ingestion loop (every %ds)", interval_seconds)
    while True:
        try:
            counts = await fetch_and_store_feeds()
            if counts:
                logger.info("News feed cycle complete: %s", counts)
        except Exception as exc:
            logger.error("News feed cycle failed: %s", exc)
        await asyncio.sleep(interval_seconds)
