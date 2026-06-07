"""
News API — thin route handlers.

Business logic lives in ``backend.services.news_service``.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services import news_service

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/latest")
async def get_latest_news(
    limit: int = Query(50, ge=1, le=200, description="Number of articles to return"),
    source: Optional[str] = Query(None, description="Filter by source name"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTC, ETH)"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
):
    """Get latest news articles."""
    try:
        return await news_service.get_latest(limit=limit, source=source, symbol=symbol, hours=hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_news_sources():
    """Get list of all news sources."""
    return await news_service.get_sources()


@router.get("/trending")
async def get_trending_news(
    limit: int = Query(10, ge=1, le=50, description="Number of trending articles"),
):
    """Get trending news (most mentioned symbols, highest sentiment)."""
    try:
        return await news_service.get_trending(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/{symbol}")
async def get_symbol_sentiment(
    symbol: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Get sentiment analysis for a specific symbol."""
    try:
        return await news_service.get_symbol_sentiment(symbol=symbol, hours=hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_news(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
):
    """Search news articles by keyword."""
    try:
        return await news_service.search_news(query=q, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
