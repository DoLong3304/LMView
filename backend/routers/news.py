"""
News API Endpoints
Separate from trading endpoints for clean architecture
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["news"])


# In-memory cache for news (will be replaced with Redis)
news_cache = {
    "articles": [],
    "last_update": None
}


@router.get("/latest")
async def get_latest_news(
    limit: int = Query(50, ge=1, le=200, description="Number of articles to return"),
    source: Optional[str] = Query(None, description="Filter by source name"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTC, ETH)"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """
    Get latest news articles

    **Parameters:**
    - `limit`: Number of articles (1-200)
    - `source`: Filter by source (e.g., "CoinDesk", "CoinTelegraph")
    - `symbol`: Filter by cryptocurrency symbol (e.g., "BTC", "ETH")
    - `hours`: Hours to look back (1-168)

    **Returns:**
    ```json
    {
        "total": 150,
        "articles": [
            {
                "id": "abc123",
                "source": "CoinDesk",
                "title": "Bitcoin Reaches New High",
                "summary": "Bitcoin price surged...",
                "url": "https://coindesk.com/...",
                "author": "John Doe",
                "published_at": 1715443200000,
                "image_url": "https://...",
                "tags": ["bitcoin", "price"],
                "symbols": ["BTC"],
                "sentiment_score": 0.75,
                "sentiment_label": "positive"
            }
        ],
        "last_update": "2026-05-11T10:30:00Z"
    }
    ```
    """
    try:
        articles = news_cache.get("articles", [])

        # Filter by time
        cutoff_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
        filtered = [a for a in articles if a.get("published_at", 0) >= cutoff_time]

        # Filter by source
        if source:
            filtered = [a for a in filtered if a.get("source", "").lower() == source.lower()]

        # Filter by symbol
        if symbol:
            symbol_upper = symbol.upper()
            filtered = [a for a in filtered if symbol_upper in a.get("symbols", [])]

        # Limit results
        filtered = filtered[:limit]

        return {
            "total": len(filtered),
            "articles": filtered,
            "last_update": news_cache.get("last_update")
        }

    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_news_sources():
    """
    Get list of all news sources with health status

    **Returns:**
    ```json
    {
        "total_sources": 12,
        "healthy_sources": 11,
        "sources": [
            {
                "name": "CoinDesk",
                "type": "rss",
                "language": "en",
                "region": "global",
                "fetch_count": 150,
                "error_count": 0,
                "last_fetch": "2026-05-11T10:25:00Z",
                "health": "healthy"
            }
        ]
    }
    ```
    """
    # This will be populated by the scraper
    sources = [
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
        {"name": "CryptoNews", "type": "rss", "language": "en", "region": "global"}
    ]

    return {
        "total_sources": len(sources),
        "healthy_sources": len(sources),  # Will be calculated from actual health
        "sources": sources
    }


@router.get("/trending")
async def get_trending_news(
    limit: int = Query(10, ge=1, le=50, description="Number of trending articles")
):
    """
    Get trending news (most mentioned symbols, highest sentiment)

    **Returns:**
    ```json
    {
        "trending_articles": [...],
        "trending_symbols": [
            {"symbol": "BTC", "mention_count": 45, "avg_sentiment": 0.65},
            {"symbol": "ETH", "mention_count": 32, "avg_sentiment": 0.52}
        ]
    }
    ```
    """
    try:
        articles = news_cache.get("articles", [])

        # Get recent articles (last 24h)
        cutoff_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
        recent = [a for a in articles if a.get("published_at", 0) >= cutoff_time]

        # Sort by sentiment score (highest first)
        trending = sorted(recent, key=lambda x: abs(x.get("sentiment_score", 0)), reverse=True)[:limit]

        # Calculate trending symbols
        symbol_stats = {}
        for article in recent:
            for symbol in article.get("symbols", []):
                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {"count": 0, "sentiment_sum": 0}
                symbol_stats[symbol]["count"] += 1
                symbol_stats[symbol]["sentiment_sum"] += article.get("sentiment_score", 0)

        trending_symbols = [
            {
                "symbol": symbol,
                "mention_count": stats["count"],
                "avg_sentiment": stats["sentiment_sum"] / stats["count"] if stats["count"] > 0 else 0
            }
            for symbol, stats in symbol_stats.items()
        ]
        trending_symbols.sort(key=lambda x: x["mention_count"], reverse=True)

        return {
            "trending_articles": trending,
            "trending_symbols": trending_symbols[:10]
        }

    except Exception as e:
        logger.error(f"Error fetching trending news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/{symbol}")
async def get_symbol_sentiment(
    symbol: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze")
):
    """
    Get sentiment analysis for a specific symbol

    **Parameters:**
    - `symbol`: Cryptocurrency symbol (e.g., "BTC", "ETH")
    - `hours`: Hours to analyze (1-168)

    **Returns:**
    ```json
    {
        "symbol": "BTC",
        "article_count": 45,
        "avg_sentiment": 0.65,
        "sentiment_distribution": {
            "positive": 30,
            "neutral": 10,
            "negative": 5
        },
        "sentiment_trend": [
            {"timestamp": 1715443200000, "sentiment": 0.7},
            {"timestamp": 1715446800000, "sentiment": 0.6}
        ]
    }
    ```
    """
    try:
        articles = news_cache.get("articles", [])
        symbol_upper = symbol.upper()

        # Filter by symbol and time
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
                "sentiment_trend": []
            }

        # Calculate average sentiment
        sentiments = [a.get("sentiment_score", 0) for a in filtered]
        avg_sentiment = sum(sentiments) / len(sentiments)

        # Distribution
        positive = len([s for s in sentiments if s > 0.05])
        negative = len([s for s in sentiments if s < -0.05])
        neutral = len(sentiments) - positive - negative

        # Trend (hourly buckets)
        trend = []
        for i in range(hours):
            bucket_start = int((datetime.now() - timedelta(hours=hours-i)).timestamp() * 1000)
            bucket_end = int((datetime.now() - timedelta(hours=hours-i-1)).timestamp() * 1000)

            bucket_articles = [
                a for a in filtered
                if bucket_start <= a.get("published_at", 0) < bucket_end
            ]

            if bucket_articles:
                bucket_sentiment = sum(a.get("sentiment_score", 0) for a in bucket_articles) / len(bucket_articles)
                trend.append({
                    "timestamp": bucket_start,
                    "sentiment": round(bucket_sentiment, 3),
                    "article_count": len(bucket_articles)
                })

        return {
            "symbol": symbol_upper,
            "article_count": len(filtered),
            "avg_sentiment": round(avg_sentiment, 3),
            "sentiment_distribution": {
                "positive": positive,
                "neutral": neutral,
                "negative": negative
            },
            "sentiment_trend": trend
        }

    except Exception as e:
        logger.error(f"Error analyzing sentiment for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_news(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Number of results")
):
    """
    Search news articles by keyword

    **Parameters:**
    - `q`: Search query (minimum 2 characters)
    - `limit`: Number of results (1-200)

    **Returns:**
    ```json
    {
        "query": "bitcoin",
        "total": 45,
        "articles": [...]
    }
    ```
    """
    try:
        articles = news_cache.get("articles", [])
        query_lower = q.lower()

        # Search in title, summary, and tags
        results = [
            a for a in articles
            if query_lower in a.get("title", "").lower() or
               query_lower in a.get("summary", "").lower() or
               any(query_lower in tag.lower() for tag in a.get("tags", []))
        ]

        results = results[:limit]

        return {
            "query": q,
            "total": len(results),
            "articles": results
        }

    except Exception as e:
        logger.error(f"Error searching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function to update cache (called by background task)
def update_news_cache(articles: List[dict]):
    """Update in-memory news cache"""
    news_cache["articles"] = articles
    news_cache["last_update"] = datetime.now().isoformat()
    logger.info(f"📰 Updated news cache with {len(articles)} articles")
