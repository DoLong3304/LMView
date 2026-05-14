"""
Market metrics API — thin route handlers.

Business logic lives in ``backend.services.market_service``.
"""
from fastapi import APIRouter, HTTPException, Query

from backend.services import market_service

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview")
async def get_market_overview():
    """Get overall market overview."""
    try:
        return market_service.get_overview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_all_metrics(
    limit: int = Query(100, ge=1, le=500, description="Number of symbols to return"),
    sort_by: str = Query("rank", description="Sort by: rank, change_24h_pct, volume_24h, market_cap"),
):
    """Get metrics for all symbols."""
    try:
        return market_service.get_metrics(limit=limit, sort_by=sort_by)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gainers")
async def get_top_gainers(
    limit: int = Query(10, ge=1, le=50, description="Number of top gainers"),
    timeframe: str = Query("24h", description="Timeframe: 1h, 24h, 7d"),
):
    """Get top gainers."""
    try:
        return market_service.get_top_gainers(limit=limit, timeframe=timeframe)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/losers")
async def get_top_losers(
    limit: int = Query(10, ge=1, le=50, description="Number of top losers"),
    timeframe: str = Query("24h", description="Timeframe: 1h, 24h, 7d"),
):
    """Get top losers."""
    try:
        return market_service.get_top_losers(limit=limit, timeframe=timeframe)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbol/{symbol}")
async def get_symbol_metrics(symbol: str):
    """Get metrics for a specific symbol."""
    result = market_service.get_symbol_metrics(symbol)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return result


@router.get("/heatmap")
async def get_market_heatmap(
    limit: int = Query(100, ge=10, le=200, description="Number of symbols"),
):
    """Get market heatmap data (for visualization)."""
    try:
        return market_service.get_heatmap(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
