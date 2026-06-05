"""
Market Overview API - Comprehensive market metrics for Overview tab
Aggregates data from multiple Gold tables
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta

import asyncio
from backend.core.database import get_trino_connection

router = APIRouter(prefix="/api/market", tags=["market-overview"])
logger = logging.getLogger(__name__)

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



@router.get("/overview")
async def get_market_overview(
    timeframe: str = Query("24h", description="Timeframe: 1h, 24h, 7d"),
    limit: int = Query(10, ge=5, le=50, description="Number of items per category")
):
    """
    Get comprehensive market overview with all metrics for Overview tab.
    Tries Trino gold tables first, falls back to Redis ticker cache.
    """
    try:
        trino = await get_trino()
        used_source = "trino_gold"

        market_summary = await _get_market_summary(trino)
        top_gainers = await _get_top_movers(trino, "gainer", timeframe, limit)
        top_losers = await _get_top_movers(trino, "loser", timeframe, limit)
        most_volatile = await _get_most_volatile(trino, limit)
        highest_volume = await _get_highest_volume(trino, limit)
        trending_news = await _get_trending_news(trino, limit)
        sector_performance = await _get_sector_performance(trino)
        heatmap_data = await _get_heatmap_data(trino, limit)
        indicators_summary = await _get_indicators_summary(trino)

        has_trino_data = (
            market_summary.get("total_volume_24h", 0) > 0 or
            market_summary.get("active_symbols", 0) > 0 or
            len(top_gainers) > 0
        )
        if not has_trino_data:
            logger.info("Trino gold tables empty, deriving from Redis ticker cache")
            market_summary, top_gainers, top_losers, most_volatile, highest_volume = (
                await _derive_market_from_redis(timeframe, limit)
            )
            trending_news = []
            sector_performance = {}
            heatmap_data = []
            used_source = "ticker_derived"

    except Exception as e:
        logger.warning("Trino gold query failed (%s), falling back to Redis/ticker", e)
        try:
            market_summary, top_gainers, top_losers, most_volatile, highest_volume = (
                await _derive_market_from_redis(timeframe, limit)
            )
        except Exception:
            market_summary = {
                "total_market_cap": 0, "total_volume_24h": 0,
                "btc_dominance": 0, "eth_dominance": 0,
                "active_symbols": 0, "fear_greed_index": 50,
            }
            top_gainers = []; top_losers = []; most_volatile = []; highest_volume = []
        trending_news = []; sector_performance = {}; heatmap_data = []
        indicators_summary = {
            "total_symbols": 0, "avg_rsi": 50,
            "overbought_count": 0, "oversold_count": 0,
            "bullish_macd_count": 0, "bearish_macd_count": 0,
        }
        used_source = "ticker_derived"

    return {
        "timestamp": datetime.now().isoformat(),
        "timeframe": timeframe,
        "market_summary": market_summary,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "most_volatile": most_volatile,
        "highest_volume": highest_volume,
        "trending_news": trending_news,
        "sector_performance": sector_performance,
        "heatmap_data": heatmap_data,
        "indicators_summary": indicators_summary,
        "metadata": {
            "source": used_source,
            "is_placeholder": used_source == "ticker_derived",
            "warning": None if used_source == "trino_gold" else
                "Fallback: data derived from live ticker Redis cache. Connect Trino gold tables for full analytics.",
        },
    }


async def _get_market_summary(trino) -> Dict[str, Any]:
    """Get market summary metrics"""
    query = """
    SELECT
        total_market_cap,
        total_volume_24h,
        btc_dominance_pct,
        eth_dominance_pct,
        active_symbols
    FROM iceberg.gold.market_dominance
    ORDER BY snapshot_time DESC
    LIMIT 1
    """

    result = await trino.fetch_one(query)

    if not result:
        return {
            "total_market_cap": 0,
            "total_volume_24h": 0,
            "btc_dominance": 0,
            "eth_dominance": 0,
            "active_symbols": 0,
            "fear_greed_index": 50
        }

    # Calculate Fear & Greed Index (simplified)
    # Based on: volatility (30%), volume (25%), dominance (25%), sentiment (20%)
    fear_greed = 50  # Neutral baseline

    return {
        "total_market_cap": float(result[0]) if result[0] else 0,
        "total_volume_24h": float(result[1]) if result[1] else 0,
        "btc_dominance": float(result[2]) if result[2] else 0,
        "eth_dominance": float(result[3]) if result[3] else 0,
        "active_symbols": int(result[4]) if result[4] else 0,
        "fear_greed_index": fear_greed
    }


async def _get_top_movers(trino, category: str, timeframe: str, limit: int) -> List[Dict[str, Any]]:
    """Get top gainers or losers"""
    query = f"""
    SELECT
        symbol,
        rank,
        change_pct,
        current_price,
        volume_24h,
        volume_change_pct
    FROM iceberg.gold.movers_ranking
    WHERE category = '{category}'
      AND timeframe = '{timeframe}'
      AND _partition_date = CURRENT_DATE
    ORDER BY rank
    LIMIT {limit}
    """

    results = await trino.fetch_all(query)

    return [
        {
            "symbol": row[0],
            "rank": row[1],
            "change_pct": round(float(row[2]), 2) if row[2] else 0,
            "price": round(float(row[3]), 2) if row[3] else 0,
            "volume_24h": round(float(row[4]), 2) if row[4] else 0,
            "volume_change_pct": round(float(row[5]), 2) if row[5] else 0
        }
        for row in results
    ]


async def _get_most_volatile(trino, limit: int) -> List[Dict[str, Any]]:
    """Get most volatile symbols"""
    query = f"""
    SELECT
        symbol,
        volatility_24h,
        price_range_pct_24h,
        rank_by_volatility
    FROM iceberg.gold.volatility_ranking
    WHERE _partition_date = CURRENT_DATE
    ORDER BY rank_by_volatility
    LIMIT {limit}
    """

    results = await trino.fetch_all(query)

    return [
        {
            "symbol": row[0],
            "volatility_24h": round(float(row[1]), 4) if row[1] else 0,
            "price_range_pct": round(float(row[2]), 2) if row[2] else 0,
            "rank": row[3]
        }
        for row in results
    ]


async def _get_highest_volume(trino, limit: int) -> List[Dict[str, Any]]:
    """Get symbols with highest volume"""
    query = f"""
    SELECT
        symbol,
        volume_24h,
        current_price,
        change_pct
    FROM iceberg.gold.movers_ranking
    WHERE timeframe = '24h'
      AND _partition_date = CURRENT_DATE
    ORDER BY volume_24h DESC
    LIMIT {limit}
    """

    results = await trino.fetch_all(query)

    return [
        {
            "symbol": row[0],
            "volume_24h": round(float(row[1]), 2) if row[1] else 0,
            "price": round(float(row[2]), 2) if row[2] else 0,
            "change_pct": round(float(row[3]), 2) if row[3] else 0
        }
        for row in results
    ]


async def _get_trending_news(trino, limit: int) -> List[Dict[str, Any]]:
    """Get trending news by symbol"""
    query = f"""
    SELECT
        symbol,
        article_count,
        avg_sentiment,
        sentiment_positive,
        sentiment_negative
    FROM iceberg.gold.news_sentiment_daily
    WHERE date = CURRENT_DATE
    ORDER BY article_count DESC
    LIMIT {limit}
    """

    results = await trino.fetch_all(query)

    return [
        {
            "symbol": row[0],
            "article_count": row[1],
            "avg_sentiment": round(float(row[2]), 3) if row[2] else 0,
            "sentiment_positive": row[3],
            "sentiment_negative": row[4]
        }
        for row in results
    ]


async def _get_sector_performance(trino) -> Dict[str, Any]:
    """Get sector performance metrics"""
    query = """
    SELECT
        sector,
        avg_change_pct,
        total_volume,
        symbol_count
    FROM iceberg.gold.sector_performance
    WHERE _partition_date = CURRENT_DATE
    ORDER BY snapshot_time DESC
    LIMIT 3
    """

    results = await trino.fetch_all(query)

    sectors = {}
    for row in results:
        sectors[row[0].lower().replace(" ", "_")] = {
            "change_pct": round(float(row[1]), 2) if row[1] else 0,
            "volume": round(float(row[2]), 2) if row[2] else 0,
            "symbol_count": row[3]
        }

    return sectors


async def _get_heatmap_data(trino, limit: int) -> List[Dict[str, Any]]:
    """Get heatmap data (symbol, change, volume, market cap)"""
    query = f"""
    SELECT
        m.symbol,
        m.change_pct,
        m.current_price,
        m.volume_24h,
        (m.current_price * m.volume_24h * 10) as market_cap,
        v.volatility_24h
    FROM iceberg.gold.movers_ranking m
    LEFT JOIN iceberg_catalog.gold.volatility_ranking v
        ON m.symbol = v.symbol
        AND m._partition_date = v._partition_date
    WHERE m.timeframe = '24h'
      AND m._partition_date = CURRENT_DATE
    ORDER BY market_cap DESC
    LIMIT {limit}
    """

    results = await trino.fetch_all(query)

    return [
        {
            "symbol": row[0],
            "change_pct": round(float(row[1]), 2) if row[1] else 0,
            "price": round(float(row[2]), 2) if row[2] else 0,
            "volume_24h": round(float(row[3]), 2) if row[3] else 0,
            "market_cap": round(float(row[4]), 2) if row[4] else 0,
            "volatility": round(float(row[5]), 4) if row[5] else 0
        }
        for row in results
    ]


async def _get_indicators_summary(trino) -> Dict[str, Any]:
    """Get technical indicators summary"""
    query = """
    SELECT
        COUNT(*) as total_symbols,
        AVG(rsi_14) as avg_rsi,
        SUM(CASE WHEN rsi_14 > 70 THEN 1 ELSE 0 END) as overbought_count,
        SUM(CASE WHEN rsi_14 < 30 THEN 1 ELSE 0 END) as oversold_count,
        SUM(CASE WHEN macd > macd_signal THEN 1 ELSE 0 END) as bullish_macd_count,
        SUM(CASE WHEN macd < macd_signal THEN 1 ELSE 0 END) as bearish_macd_count
    FROM iceberg.gold.momentum_indicators
    WHERE _partition_date = CURRENT_DATE
    """

    result = await trino.fetch_one(query)

    if not result:
        return {
            "total_symbols": 0,
            "avg_rsi": 50,
            "overbought_count": 0,
            "oversold_count": 0,
            "bullish_macd_count": 0,
            "bearish_macd_count": 0
        }

    return {
        "total_symbols": result[0],
        "avg_rsi": round(float(result[1]), 2) if result[1] else 50,
        "overbought_count": result[2],
        "oversold_count": result[3],
        "bullish_macd_count": result[4],
        "bearish_macd_count": result[5]
    }



async def _derive_market_from_redis(timeframe: str, limit: int):
    """Derive market overview from Redis ticker:latest scan when Trino gold tables are empty.

    Returns (market_summary, top_gainers, top_losers, most_volatile, highest_volume).
    """
    from backend.core.database import get_redis
    r = await get_redis()

    # Scan ticker:latest:*:*
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
        exchange = key.split(":")[-2] if len(key.split(":")) >= 3 else "unknown"
        try:
            price = float(data.get("price", 0))
            volume = float(data.get("volume", 0))  # h24_volume
            change24h = float(data.get("change24h", 0))
            bid = float(data.get("bid", 0))
            ask = float(data.get("ask", 0))
        except (ValueError, TypeError):
            continue
        tickers.append({
            "symbol": symbol,
            "exchange": exchange,
            "price": price,
            "volume_24h": volume,
            "change_pct": change24h,
            "spread": round(ask - bid, 8) if bid > 0 and ask > 0 else 0,
        })

    if not tickers:
        return (
            {"total_market_cap": 0, "total_volume_24h": 0, "btc_dominance": 0, "eth_dominance": 0, "active_symbols": 0, "fear_greed_index": 50},
            [], [], [], [],
        )

    total_volume = sum(t["volume_24h"] for t in tickers)
    active = len(tickers)

    # Top gainers/losers
    sorted_change = sorted(tickers, key=lambda t: t["change_pct"], reverse=True)
    top_gainers = sorted_change[:limit]
    top_losers = sorted_change[-limit:][::-1]

    # Most volatile (by absolute change + spread)
    for t in tickers:
        t["volatility"] = round(abs(t["change_pct"]) + t["spread"] / (t["price"] or 1) * 100, 4)
    most_volatile = sorted(tickers, key=lambda t: t["volatility"], reverse=True)[:limit]
    for t in top_gainers + top_losers + most_volatile:
        t.pop("spread", None)

    # Highest volume
    highest_volume = sorted(tickers, key=lambda t: t["volume_24h"], reverse=True)[:limit]

    # BTC/ETH dominance
    btc = next((t for t in tickers if t["symbol"] == "BTCUSDT"), None)
    eth = next((t for t in tickers if t["symbol"] == "ETHUSDT"), None)
    btc_dom = (btc["volume_24h"] / total_volume * 100) if btc and total_volume > 0 else 0
    eth_dom = (eth["volume_24h"] / total_volume * 100) if eth and total_volume > 0 else 0

    market_summary = {
        "total_market_cap": 0,
        "total_volume_24h": round(total_volume, 2),
        "btc_dominance": round(btc_dom, 2),
        "eth_dominance": round(eth_dom, 2),
        "active_symbols": active,
        "fear_greed_index": 50,
    }

    return market_summary, top_gainers, top_losers, most_volatile, highest_volume

@router.get("/heatmap")
async def get_heatmap(
    limit: int = Query(50, ge=10, le=200, description="Number of symbols")
):
    """Get heatmap data for visualization"""
    try:
        trino = await get_trino()
        heatmap_data = await _get_heatmap_data(trino, limit)

        return {
            "timestamp": datetime.now().isoformat(),
            "data": heatmap_data
        }
    except Exception as e:
        logger.error(f"Failed to get heatmap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rankings/{category}")
async def get_rankings(
    category: str,
    timeframe: str = Query("24h", description="Timeframe: 1h, 24h, 7d"),
    limit: int = Query(20, ge=5, le=100)
):
    """
    Get rankings by category

    Categories: gainers, losers, volume, volatile
    """
    try:
        trino = await get_trino()

        if category == "gainers":
            data = await _get_top_movers(trino, "gainer", timeframe, limit)
        elif category == "losers":
            data = await _get_top_movers(trino, "loser", timeframe, limit)
        elif category == "volume":
            data = await _get_highest_volume(trino, limit)
        elif category == "volatile":
            data = await _get_most_volatile(trino, limit)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

        return {
            "category": category,
            "timeframe": timeframe,
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rankings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
