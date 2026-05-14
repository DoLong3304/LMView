"""
News service — business logic for news articles, sentiment, search.
"""
from datetime import datetime, timedelta
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


# In-memory cache for news (will be replaced with Redis)
_news_cache = {
    "articles": [],
    "last_update": None
}

# Available news sources
NEWS_SOURCES = [
    {"name": "CryptoPanic", "type": "api", "language": "en", "region": "global"},
    {"name": "CoinDesk", "type": "rss", "language": "en", "region": "global"},
    {"name": "CoinTelegraph", "type": "rss", "language": "en", "region": "global"},
    {"name": "Decrypt", "type": "rss", "language": "en", "region": "global"},
    {"name": "The Block", "type": "rss", "language": "en", "region": "global"},
    {"name": "Bitcoin Magazine", "type": "rss", "language": "en", "region": "global"},
    {"name": "CryptoSlate", "type": "rss", "language": "en", "region": "global"},
    {"name": "BeInCrypto", "type": "rss", "language": "en", "region": "global"},
    {"name": "NewsBTC", "type": "rss", "language": "en", "region": "global"},
    {"name": "U.Today", "type": "rss", "language": "en", "region": "global"},
    {"name": "Bitcoinist", "type": "rss", "language": "en", "region": "global"},
    {"name": "CryptoNews", "type": "rss", "language": "en", "region": "global"},
]


def get_latest(
    limit: int = 50,
    source: Optional[str] = None,
    symbol: Optional[str] = None,
    hours: int = 24,
) -> dict:
    """Get latest news articles with optional filters."""
    articles = _news_cache.get("articles", [])

    cutoff_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
    filtered = [a for a in articles if a.get("published_at", 0) >= cutoff_time]

    if source:
        filtered = [a for a in filtered if a.get("source", "").lower() == source.lower()]
    if symbol:
        symbol_upper = symbol.upper()
        filtered = [a for a in filtered if symbol_upper in a.get("symbols", [])]

    return {
        "total": len(filtered[:limit]),
        "articles": filtered[:limit],
        "last_update": _news_cache.get("last_update"),
    }


def get_sources() -> dict:
    """Return list of all news sources."""
    return {
        "total_sources": len(NEWS_SOURCES),
        "healthy_sources": len(NEWS_SOURCES),
        "sources": NEWS_SOURCES,
    }


def get_trending(limit: int = 10) -> dict:
    """Get trending articles and symbol mention stats."""
    articles = _news_cache.get("articles", [])

    cutoff_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
    recent = [a for a in articles if a.get("published_at", 0) >= cutoff_time]

    trending = sorted(
        recent, key=lambda x: abs(x.get("sentiment_score", 0)), reverse=True
    )[:limit]

    symbol_stats: dict = {}
    for article in recent:
        for sym in article.get("symbols", []):
            if sym not in symbol_stats:
                symbol_stats[sym] = {"count": 0, "sentiment_sum": 0}
            symbol_stats[sym]["count"] += 1
            symbol_stats[sym]["sentiment_sum"] += article.get("sentiment_score", 0)

    trending_symbols = [
        {
            "symbol": sym,
            "mention_count": s["count"],
            "avg_sentiment": s["sentiment_sum"] / s["count"] if s["count"] > 0 else 0,
        }
        for sym, s in symbol_stats.items()
    ]
    trending_symbols.sort(key=lambda x: x["mention_count"], reverse=True)

    return {"trending_articles": trending, "trending_symbols": trending_symbols[:10]}


def get_symbol_sentiment(symbol: str, hours: int = 24) -> dict:
    """Get sentiment analysis for a specific symbol."""
    articles = _news_cache.get("articles", [])
    symbol_upper = symbol.upper()

    cutoff_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
    filtered = [
        a for a in articles
        if symbol_upper in a.get("symbols", []) and a.get("published_at", 0) >= cutoff_time
    ]

    if not filtered:
        return {
            "symbol": symbol_upper,
            "article_count": 0,
            "avg_sentiment": 0,
            "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "sentiment_trend": [],
        }

    sentiments = [a.get("sentiment_score", 0) for a in filtered]
    avg_sentiment = sum(sentiments) / len(sentiments)

    positive = len([s for s in sentiments if s > 0.05])
    negative = len([s for s in sentiments if s < -0.05])
    neutral = len(sentiments) - positive - negative

    trend = []
    for i in range(hours):
        bucket_start = int((datetime.now() - timedelta(hours=hours - i)).timestamp() * 1000)
        bucket_end = int((datetime.now() - timedelta(hours=hours - i - 1)).timestamp() * 1000)
        bucket_articles = [
            a for a in filtered
            if bucket_start <= a.get("published_at", 0) < bucket_end
        ]
        if bucket_articles:
            bucket_sentiment = sum(a.get("sentiment_score", 0) for a in bucket_articles) / len(bucket_articles)
            trend.append({
                "timestamp": bucket_start,
                "sentiment": round(bucket_sentiment, 3),
                "article_count": len(bucket_articles),
            })

    return {
        "symbol": symbol_upper,
        "article_count": len(filtered),
        "avg_sentiment": round(avg_sentiment, 3),
        "sentiment_distribution": {"positive": positive, "neutral": neutral, "negative": negative},
        "sentiment_trend": trend,
    }


def search_news(query: str, limit: int = 50) -> dict:
    """Search news articles by keyword."""
    articles = _news_cache.get("articles", [])
    query_lower = query.lower()
    results = [
        a for a in articles
        if query_lower in a.get("title", "").lower()
        or query_lower in a.get("summary", "").lower()
        or any(query_lower in tag.lower() for tag in a.get("tags", []))
    ][:limit]
    return {"query": query, "total": len(results), "articles": results}


def update_news_cache(articles: List[dict]):
    """Update in-memory news cache (called by background task)."""
    _news_cache["articles"] = articles
    _news_cache["last_update"] = datetime.now().isoformat()
    logger.info("Updated news cache with %d articles", len(articles))
