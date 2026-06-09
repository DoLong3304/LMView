"""
Screener API - Filter symbols by technical indicators and metrics.
Provides endpoints for advanced filtering beyond simple ranking.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

import asyncio
from backend.core.database import get_redis, get_trino_connection

router = APIRouter(prefix="/api/screener", tags=["screener"])
logger = logging.getLogger(__name__)

DB = "iceberg.crypto_lakehouse"
GOLD_FRESHNESS_MINUTES = 30


class AsyncTrinoClient:
    def __init__(self):
        self.conn = get_trino_connection()

    async def fetch_one(self, query: str):
        def _fetch():
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor.fetchone()
        return await asyncio.to_thread(_fetch)

    async def fetch_all(self, query: str):
        def _fetch():
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
        return await asyncio.to_thread(_fetch)


async def get_trino():
    return AsyncTrinoClient()


@router.get("/symbols")
async def get_screened_symbols(
    # Trend filters
    trend: Optional[str] = Query(None, description="Filter by trend: bullish, bearish, neutral"),
    # RSI filters
    rsi_min: Optional[float] = Query(None, description="Minimum RSI (0-100)"),
    rsi_max: Optional[float] = Query(None, description="Maximum RSI (0-100)"),
    # Price filters
    price_min: Optional[float] = Query(None, description="Minimum price"),
    price_max: Optional[float] = Query(None, description="Maximum price"),
    # Volume filters
    volume_min: Optional[float] = Query(None, description="Minimum 24h volume"),
    # Change filters
    change_min: Optional[float] = Query(None, description="Minimum 24h change %"),
    change_max: Optional[float] = Query(None, description="Maximum 24h change %"),
    # Market cap filters
    market_cap_min: Optional[float] = Query(None, description="Minimum market cap"),
    # Volatility filters
    volatility_max: Optional[float] = Query(None, description="Maximum volatility %"),
    # Sort options
    sort_by: str = Query("volume_24h", description="Sort field: volume_24h, change_24h, price, rsi, market_cap"),
    sort_dir: str = Query("desc", description="Sort direction: asc, desc"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    """
    Get screened symbols based on technical filters.
    Falls back to Redis ticker data if gold tables unavailable.
    """
    # Build Trino query if gold tables available
    trino_data = []
    use_trino = False

    try:
        trino = await get_trino()
        conditions = []

        if rsi_min is not None:
            conditions.append(f"rsi_14 >= {rsi_min}")
        if rsi_max is not None:
            conditions.append(f"rsi_14 <= {rsi_max}")
        if change_min is not None:
            conditions.append(f"change_24h >= {change_min}")
        if change_max is not None:
            conditions.append(f"change_24h <= {change_max}")
        if volume_min is not None:
            conditions.append(f"volume_24h >= {volume_min}")
        if market_cap_min is not None:
            conditions.append(f"market_cap >= {market_cap_min}")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_dir = "DESC" if sort_dir == "desc" else "ASC"

        # Map sort_by to column name
        sort_col_map = {
            "volume_24h": "volume_24h",
            "change_24h": "change_24h",
            "price": "price",
            "rsi": "rsi_14",
            "market_cap": "market_cap",
            "volatility": "volatility_24h",
        }
        sort_col = sort_col_map.get(sort_by, "volume_24h")

        query = f"""
        SELECT
            symbol,
            exchange,
            price,
            change_24h,
            change_7d,
            volume_24h,
            market_cap,
            rsi_14,
            volatility_24h,
            trend_signal,
            sma_20,
            sma_50,
            support,
            resistance
        FROM {DB}.gold_momentum_indicators
        WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
          AND {where_clause}
        ORDER BY {sort_col} {order_dir}
        LIMIT {limit}
        """

        trino_data = await trino.fetch_all(query)
        if trino_data:
            use_trino = True
    except Exception as e:
        logger.warning("Trino gold query failed for screener, using Redis fallback: %s", e)

    if use_trino:
        results = [
            {
                "symbol": row[0],
                "exchange": row[1],
                "price": round(float(row[2]), 8) if row[2] else 0,
                "change_24h": round(float(row[3]), 2) if row[3] else 0,
                "change_7d": round(float(row[4]), 2) if row[4] else None,
                "volume_24h": round(float(row[5]), 2) if row[5] else 0,
                "market_cap": round(float(row[6]), 2) if row[6] else None,
                "rsi_14": round(float(row[7]), 1) if row[7] else None,
                "volatility_24h": round(float(row[8]), 2) if row[8] else None,
                "trend": row[9] if row[9] else "neutral",
                "sma_20": round(float(row[10]), 8) if row[10] else None,
                "sma_50": round(float(row[11]), 8) if row[11] else None,
                "support": round(float(row[12]), 8) if row[12] else None,
                "resistance": round(float(row[13]), 8) if row[13] else None,
            }
            for row in trino_data
        ]
    else:
        # Fallback to Redis ticker data
        results = await _get_screened_from_redis(
            trend=trend,
            price_min=price_min,
            price_max=price_max,
            volume_min=volume_min,
            change_min=change_min,
            change_max=change_max,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
        )

    # Apply trend filter if specified (can be applied to both paths)
    if trend:
        trend_lower = trend.lower()
        if use_trino:
            # Already filtered in query
            pass
        else:
            results = [r for r in results if r.get("trend", "neutral") == trend_lower]

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "filters": {
            "trend": trend,
            "rsi_min": rsi_min,
            "rsi_max": rsi_max,
            "price_min": price_min,
            "price_max": price_max,
            "volume_min": volume_min,
            "change_min": change_min,
            "change_max": change_max,
            "market_cap_min": market_cap_min,
        },
        "count": len(results),
        "data": results,
    }


async def _get_screened_from_redis(
    trend: Optional[str],
    price_min: Optional[float],
    price_max: Optional[float],
    volume_min: Optional[float],
    change_min: Optional[float],
    change_max: Optional[float],
    sort_by: str,
    sort_dir: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Fallback: derive screened symbols from Redis ticker data."""
    r = await get_redis()

    keys = []
    cursor = 0
    while True:
        cursor, batch = await r.scan(cursor, match="ticker:latest:*:*", count=200)
        keys.extend(batch)
        if cursor == 0:
            break

    tickers = []
    for key in keys:
        data = await r.hgetall(key)
        if not data:
            continue
        symbol = key.split(":")[-1]
        try:
            price = float(data.get("price", 0))
            volume = float(data.get("volume", 0))
            change24h = float(data.get("change24h", 0))
        except (ValueError, TypeError):
            continue

        # Apply filters
        if price_min is not None and price < price_min:
            continue
        if price_max is not None and price > price_max:
            continue
        if volume_min is not None and volume < volume_min:
            continue
        if change_min is not None and change24h < change_min:
            continue
        if change_max is not None and change24h > change_max:
            continue

        # Calculate basic trend from change
        if change24h > 2:
            symbol_trend = "bullish"
        elif change24h < -2:
            symbol_trend = "bearish"
        else:
            symbol_trend = "neutral"

        tickers.append({
            "symbol": symbol,
            "exchange": "aggregated",
            "price": round(price, 8),
            "change_24h": round(change24h, 2),
            "volume_24h": round(volume, 2),
            "trend": symbol_trend,
        })

    # Sort
    sort_key_map = {
        "volume_24h": "volume_24h",
        "change_24h": "change_24h",
        "price": "price",
    }
    sk = sort_key_map.get(sort_by, "volume_24h")
    reverse = sort_dir == "desc"
    tickers.sort(key=lambda t: t.get(sk, 0), reverse=reverse)

    return tickers[:limit]


@router.get("/presets")
async def get_screener_presets():
    """Get available screener presets."""
    return {
        "presets": [
            {
                "id": "oversold",
                "name": "Oversold",
                "description": "RSI below 30",
                "filters": {"rsi_min": 0, "rsi_max": 30},
            },
            {
                "id": "overbought",
                "name": "Overbought",
                "description": "RSI above 70",
                "filters": {"rsi_min": 70, "rsi_max": 100},
            },
            {
                "id": "highVolume",
                "name": "High Volume",
                "description": "Volume > 100M",
                "filters": {"volume_min": 100_000_000},
            },
            {
                "id": "topGainers",
                "name": "Top Gainers",
                "description": "+5% or more 24h",
                "filters": {"change_min": 5, "change_max": 100},
            },
            {
                "id": "topLosers",
                "name": "Top Losers",
                "description": "-5% or more 24h",
                "filters": {"change_min": -100, "change_max": -5},
            },
            {
                "id": "strongBullish",
                "name": "Strong Bullish",
                "description": "Bullish trend + RSI 30-70",
                "filters": {"trend": "bullish", "rsi_min": 30, "rsi_max": 70},
            },
            {
                "id": "strongBearish",
                "name": "Strong Bearish",
                "description": "Bearish trend + RSI 30-70",
                "filters": {"trend": "bearish", "rsi_min": 30, "rsi_max": 70},
            },
        ]
    }


@router.get("/watchlist")
async def get_watchlist_with_indicators(
    symbols: str = Query(None, description="Comma-separated symbols"),
    include_indicators: bool = Query(True, description="Include technical indicators"),
):
    """
    Get watchlist data with technical indicators for specific symbols.
    Used by EnhancedWatchlist component.
    """
    r = await get_redis()

    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
    else:
        # Get all symbols
        keys = []
        cursor = 0
        while True:
            cursor, batch = await r.scan(cursor, match="ticker:latest:*:*", count=200)
            keys.extend(batch)
            if cursor == 0:
                break
        symbol_list = list(set(key.split(":")[-1] for key in keys))

    results = []
    for symbol in symbol_list[:100]:  # Limit to 100 symbols
        data = await r.hgetall(f"ticker:latest:binance:{symbol}")
        if not data:
            continue

        try:
            price = float(data.get("price", 0))
            volume = float(data.get("volume", 0))
            change24h = float(data.get("change24h", 0))
        except (ValueError, TypeError):
            continue

        # Basic trend calculation
        if change24h > 2:
            trend = "bullish"
        elif change24h < -2:
            trend = "bearish"
        else:
            trend = "neutral"

        results.append({
            "symbol": symbol,
            "name": symbol.replace("USDT", "").replace("BTC", ""),
            "price": round(price, 8),
            "change": round(change24h, 2),
            "change24h": round(change24h, 2),
            "volume24h": round(volume, 2),
            "trend": trend,
            "color": "green" if change24h >= 0 else "red",
            "activityScore": volume * (1 + abs(change24h) / 100),
        })

    # Sort by activity score
    results.sort(key=lambda x: x.get("activityScore", 0), reverse=True)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(results),
        "data": results,
    }