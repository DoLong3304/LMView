"""
Market Metrics API Endpoints
Provides market overview, top gainers/losers, price changes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])


# In-memory cache for market metrics (will be replaced with Redis)
market_cache = {
    "metrics": [],
    "summary": {},
    "top_gainers": [],
    "top_losers": [],
    "last_update": None
}


@router.get("/overview")
async def get_market_overview():
    """
    Get overall market overview

    **Returns:**
    ```json
    {
        "total_symbols": 150,
        "total_volume_24h": 125000000000,
        "total_market_cap": 2500000000000,
        "avg_change_24h_pct": 2.5,
        "gainers_count": 95,
        "losers_count": 50,
        "neutral_count": 5,
        "last_update": "2026-05-11T10:30:00Z"
    }
    ```
    """
    try:
        summary = market_cache.get("summary", {})
        summary["last_update"] = market_cache.get("last_update")
        return summary
    except Exception as e:
        logger.error(f"Error fetching market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_all_metrics(
    limit: int = Query(100, ge=1, le=500, description="Number of symbols to return"),
    sort_by: str = Query("rank", description="Sort by: rank, change_24h_pct, volume_24h, market_cap")
):
    """
    Get metrics for all symbols

    **Parameters:**
    - `limit`: Number of symbols (1-500)
    - `sort_by`: Sort field (rank, change_24h_pct, volume_24h, market_cap)

    **Returns:**
    ```json
    {
        "total": 150,
        "metrics": [
            {
                "symbol": "BTCUSDT",
                "current_price": 81234.56,
                "change_1h_pct": 0.5,
                "change_24h_pct": 2.3,
                "change_7d_pct": 5.7,
                "volume_24h": 25000000000,
                "high_24h": 82000.00,
                "low_24h": 80000.00,
                "market_cap": 1500000000000,
                "rank": 1
            }
        ]
    }
    ```
    """
    try:
        metrics = market_cache.get("metrics", [])

        # Sort
        if sort_by == "change_24h_pct":
            metrics = sorted(metrics, key=lambda x: x.get("change_24h_pct", 0), reverse=True)
        elif sort_by == "volume_24h":
            metrics = sorted(metrics, key=lambda x: x.get("volume_24h", 0), reverse=True)
        elif sort_by == "market_cap":
            metrics = sorted(metrics, key=lambda x: x.get("market_cap", 0), reverse=True)
        else:  # rank
            metrics = sorted(metrics, key=lambda x: x.get("rank", 999))

        return {
            "total": len(metrics),
            "metrics": metrics[:limit]
        }

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gainers")
async def get_top_gainers(
    limit: int = Query(10, ge=1, le=50, description="Number of top gainers"),
    timeframe: str = Query("24h", description="Timeframe: 1h, 24h, 7d")
):
    """
    Get top gainers

    **Parameters:**
    - `limit`: Number of top gainers (1-50)
    - `timeframe`: Time period (1h, 24h, 7d)

    **Returns:**
    ```json
    {
        "timeframe": "24h",
        "gainers": [
            {
                "symbol": "SOLUSDT",
                "current_price": 145.67,
                "change_24h_pct": 15.3,
                "volume_24h": 5000000000,
                "rank": 5
            }
        ]
    }
    ```
    """
    try:
        metrics = market_cache.get("metrics", [])

        # Select change field based on timeframe
        change_field = f"change_{timeframe}_pct"

        # Sort by change percentage (descending)
        gainers = sorted(
            [m for m in metrics if m.get(change_field, 0) > 0],
            key=lambda x: x.get(change_field, 0),
            reverse=True
        )[:limit]

        return {
            "timeframe": timeframe,
            "gainers": gainers
        }

    except Exception as e:
        logger.error(f"Error fetching top gainers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/losers")
async def get_top_losers(
    limit: int = Query(10, ge=1, le=50, description="Number of top losers"),
    timeframe: str = Query("24h", description="Timeframe: 1h, 24h, 7d")
):
    """
    Get top losers

    **Parameters:**
    - `limit`: Number of top losers (1-50)
    - `timeframe`: Time period (1h, 24h, 7d)

    **Returns:**
    ```json
    {
        "timeframe": "24h",
        "losers": [
            {
                "symbol": "DOGEUSDT",
                "current_price": 0.12345,
                "change_24h_pct": -8.5,
                "volume_24h": 1000000000,
                "rank": 12
            }
        ]
    }
    ```
    """
    try:
        metrics = market_cache.get("metrics", [])

        # Select change field based on timeframe
        change_field = f"change_{timeframe}_pct"

        # Sort by change percentage (ascending)
        losers = sorted(
            [m for m in metrics if m.get(change_field, 0) < 0],
            key=lambda x: x.get(change_field, 0)
        )[:limit]

        return {
            "timeframe": timeframe,
            "losers": losers
        }

    except Exception as e:
        logger.error(f"Error fetching top losers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbol/{symbol}")
async def get_symbol_metrics(symbol: str):
    """
    Get metrics for a specific symbol

    **Parameters:**
    - `symbol`: Symbol (e.g., "BTCUSDT", "ETHUSDT")

    **Returns:**
    ```json
    {
        "symbol": "BTCUSDT",
        "current_price": 81234.56,
        "price_1h_ago": 81000.00,
        "price_24h_ago": 79500.00,
        "price_7d_ago": 77000.00,
        "change_1h_pct": 0.29,
        "change_24h_pct": 2.18,
        "change_7d_pct": 5.50,
        "volume_24h": 25000000000,
        "high_24h": 82000.00,
        "low_24h": 80000.00,
        "market_cap": 1500000000000,
        "rank": 1,
        "last_updated": "2026-05-11T10:30:00Z"
    }
    ```
    """
    try:
        metrics = market_cache.get("metrics", [])
        symbol_upper = symbol.upper()

        # Find symbol
        symbol_metrics = next(
            (m for m in metrics if m.get("symbol", "").upper() == symbol_upper),
            None
        )

        if not symbol_metrics:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        return symbol_metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching symbol metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap")
async def get_market_heatmap(
    limit: int = Query(100, ge=10, le=200, description="Number of symbols")
):
    """
    Get market heatmap data (for visualization)

    **Returns:**
    ```json
    {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "change_24h_pct": 2.3,
                "market_cap": 1500000000000,
                "volume_24h": 25000000000
            }
        ]
    }
    ```
    """
    try:
        metrics = market_cache.get("metrics", [])

        # Get top symbols by market cap
        heatmap_data = sorted(
            metrics,
            key=lambda x: x.get("market_cap", 0),
            reverse=True
        )[:limit]

        # Simplify data for heatmap
        heatmap = [
            {
                "symbol": m.get("symbol"),
                "change_24h_pct": m.get("change_24h_pct", 0),
                "market_cap": m.get("market_cap", 0),
                "volume_24h": m.get("volume_24h", 0)
            }
            for m in heatmap_data
        ]

        return {"symbols": heatmap}

    except Exception as e:
        logger.error(f"Error fetching heatmap data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function to update cache (called by background task)
def update_market_cache(metrics: List[dict], summary: dict):
    """Update in-memory market cache"""
    from datetime import datetime

    # Sort by rank
    metrics_sorted = sorted(metrics, key=lambda x: x.get("rank", 999))

    # Get top gainers/losers
    top_gainers = sorted(
        [m for m in metrics if m.get("change_24h_pct", 0) > 0],
        key=lambda x: x.get("change_24h_pct", 0),
        reverse=True
    )[:10]

    top_losers = sorted(
        [m for m in metrics if m.get("change_24h_pct", 0) < 0],
        key=lambda x: x.get("change_24h_pct", 0)
    )[:10]

    market_cache["metrics"] = metrics_sorted
    market_cache["summary"] = summary
    market_cache["top_gainers"] = top_gainers
    market_cache["top_losers"] = top_losers
    market_cache["last_update"] = datetime.now().isoformat()

    logger.info(f"📊 Updated market cache with {len(metrics)} symbols")
