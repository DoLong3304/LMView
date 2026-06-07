"""
News service backed by PostgreSQL persistence.
Provides latest/trending/search/sentiment queries for news endpoints.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import json
import logging

from backend.core.postgres import get_pg_pool

logger = logging.getLogger(__name__)


def _normalize_symbol(symbol: Optional[str]) -> Optional[str]:
    if not symbol:
        return None
    cleaned = symbol.upper().replace("USDT", "").replace("USD", "")
    return cleaned or None


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _row_to_article(row) -> dict[str, Any]:
    published_at = row["published_at"].isoformat() if row["published_at"] else None
    fetched_at = row["fetched_at"].isoformat() if row["fetched_at"] else None
    raw_metadata = row["raw_metadata"] or {}
    if isinstance(raw_metadata, str):
        try:
            raw_metadata = json.loads(raw_metadata)
        except Exception:
            raw_metadata = {}
    symbols = _as_list(row["symbols"])
    tags = _as_list(row["tags"])
    symbols_mentioned = row["symbols_mentioned"] or []
    return {
        "id": str(row["id"]),
        "source": row["source"],
        "title": row["title"],
        "summary": row["summary"] or row["content_snippet"] or "",
        "url": row["url"] or "#",
        "author": raw_metadata.get("author") if isinstance(raw_metadata, dict) else None,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "image_url": raw_metadata.get("image_url") if isinstance(raw_metadata, dict) else None,
        "tags": tags,
        "symbols": symbols,
        "sentiment_score": float(row["sentiment_score"] or 0),
        "sentiment_label": row["sentiment_label"] or "neutral",
        "language": row["language"] or "en",
        "region": raw_metadata.get("region") if isinstance(raw_metadata, dict) else None,
        "symbolsMentioned": symbols_mentioned,
    }


async def get_latest(
    limit: int = 50,
    source: Optional[str] = None,
    symbol: Optional[str] = None,
    hours: int = 24,
) -> dict[str, Any]:
    pool = await get_pg_pool()
    if pool is None:
        return {"articles": [], "count": 0, "metadata": {"source": "postgres", "is_mock": False, "has_sentiment": False}}

    symbol_norm = _normalize_symbol(symbol)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with pool.acquire() as conn:
        if source and symbol_norm:
            rows = await conn.fetch(
                """
                SELECT * FROM news_articles
                WHERE published_at >= $1 AND lower(source) = lower($2) AND $3 = ANY(symbols_mentioned)
                ORDER BY published_at DESC
                LIMIT $4
                """,
                cutoff, source, symbol_norm, limit,
            )
        elif source:
            rows = await conn.fetch(
                """
                SELECT * FROM news_articles
                WHERE published_at >= $1 AND lower(source) = lower($2)
                ORDER BY published_at DESC
                LIMIT $3
                """,
                cutoff, source, limit,
            )
        elif symbol_norm:
            rows = await conn.fetch(
                """
                SELECT * FROM news_articles
                WHERE published_at >= $1 AND $2 = ANY(symbols_mentioned)
                ORDER BY published_at DESC
                LIMIT $3
                """,
                cutoff, symbol_norm, limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM news_articles
                WHERE published_at >= $1
                ORDER BY published_at DESC
                LIMIT $2
                """,
                cutoff, limit,
            )

    articles = [_row_to_article(row) for row in rows]
    return {
        "articles": articles,
        "count": len(articles),
        "metadata": {
            "source": "postgres",
            "is_mock": False,
            "has_sentiment": any(article.get("sentiment_score") is not None for article in articles),
        },
    }


async def get_sources() -> dict[str, Any]:
    pool = await get_pg_pool()
    if pool is None:
        return {"total_sources": 0, "healthy_sources": 0, "sources": []}
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT source, count(*) AS article_count, max(published_at) AS latest FROM news_articles GROUP BY source ORDER BY article_count DESC")
    sources = [
        {
            "name": row["source"],
            "article_count": row["article_count"],
            "latest_article": row["latest"].isoformat() if row["latest"] else None,
            "health": "healthy",
        }
        for row in rows
    ]
    return {"total_sources": len(sources), "healthy_sources": len(sources), "sources": sources}


async def get_trending(limit: int = 10) -> dict[str, Any]:
    pool = await get_pg_pool()
    if pool is None:
        return {"trending_articles": [], "trending_symbols": []}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    async with pool.acquire() as conn:
        article_rows = await conn.fetch(
            """
            SELECT * FROM news_articles
            WHERE published_at >= $1
            ORDER BY abs(coalesce(sentiment_score, 0)) DESC, published_at DESC
            LIMIT $2
            """,
            cutoff, limit,
        )
        symbol_rows = await conn.fetch(
            """
            SELECT symbol, COUNT(*) AS mention_count, AVG(coalesce(sentiment_score, 0)) AS avg_sentiment
            FROM (
                SELECT unnest(symbols_mentioned) AS symbol, sentiment_score
                FROM news_articles
                WHERE published_at >= $1 AND symbols_mentioned IS NOT NULL
            ) s
            GROUP BY symbol
            ORDER BY mention_count DESC, avg_sentiment DESC
            LIMIT $2
            """,
            cutoff, limit,
        )
    return {
        "trending_articles": [_row_to_article(row) for row in article_rows],
        "trending_symbols": [
            {
                "symbol": row["symbol"],
                "mention_count": row["mention_count"],
                "avg_sentiment": float(row["avg_sentiment"] or 0),
            }
            for row in symbol_rows
        ],
    }


async def get_symbol_sentiment(symbol: str, hours: int = 24) -> dict[str, Any]:
    pool = await get_pg_pool()
    symbol_norm = _normalize_symbol(symbol)
    if pool is None or not symbol_norm:
        return {"symbol": symbol_norm or symbol, "article_count": 0, "avg_sentiment": 0, "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0}, "sentiment_trend": []}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT published_at, coalesce(sentiment_score, 0) AS sentiment_score, sentiment_label
            FROM news_articles
            WHERE published_at >= $1 AND $2 = ANY(symbols_mentioned)
            ORDER BY published_at DESC
            """,
            cutoff, symbol_norm,
        )
    if not rows:
        return {"symbol": symbol_norm, "article_count": 0, "avg_sentiment": 0, "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0}, "sentiment_trend": []}

    sentiments = [float(row["sentiment_score"] or 0) for row in rows]
    positive = len([s for s in sentiments if s > 0.05])
    negative = len([s for s in sentiments if s < -0.05])
    neutral = len(sentiments) - positive - negative
    trend = [
        {
            "timestamp": row["published_at"].isoformat(),
            "sentiment": float(row["sentiment_score"] or 0),
            "article_count": 1,
        }
        for row in rows[: min(len(rows), 50)]
    ]
    return {
        "symbol": symbol_norm,
        "article_count": len(rows),
        "avg_sentiment": round(sum(sentiments) / len(sentiments), 3),
        "sentiment_distribution": {"positive": positive, "neutral": neutral, "negative": negative},
        "sentiment_trend": trend,
    }


async def search_news(query: str, limit: int = 50) -> dict[str, Any]:
    pool = await get_pg_pool()
    if pool is None:
        return {"query": query, "total": 0, "articles": []}
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM news_articles
            WHERE title ILIKE $1 OR summary ILIKE $1 OR content_snippet ILIKE $1
            ORDER BY published_at DESC
            LIMIT $2
            """,
            f"%{query}%", limit,
        )
    articles = [_row_to_article(row) for row in rows]
    return {"query": query, "total": len(articles), "articles": articles}
