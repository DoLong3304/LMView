"""
Market Overview API - Comprehensive market metrics for Overview tab.
Reads current gold-style tables from `iceberg.crypto_lakehouse.*` and keeps Redis fallback.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
import time

import asyncio
from backend.core.database import get_trino_connection
from backend.core.config import INFLUX_BUCKET
from backend.api.metrics import (
    TRINO_ACTIVE_QUERIES,
    record_trino_query,
    record_trino_fallback,
)

router = APIRouter(prefix="/api/market", tags=["market-overview"])
logger = logging.getLogger(__name__)

# P1 fix (v0.24.4): Log canonical gold schema at import time so operators
# can verify in container logs which tables the API will query.
try:
    from src.lakehouse.gold_schema_manifest import (
        list_canonical_tables,
        DEPRECATED_SPARK_TABLES,
    )
    _canonical = list_canonical_tables()
    _deprecated_count = len(DEPRECATED_SPARK_TABLES)
    logger.info(
        "market_overview: canonical Gold path active (%d tables: %s); "
        "%d Spark-based tables deprecated.",
        len(_canonical), ", ".join(_canonical), _deprecated_count,
    )
except Exception as _e:  # pragma: no cover - manifest is best-effort
    logger.debug("market_overview: gold_schema_manifest not loaded: %s", _e)

DB = "iceberg.crypto_lakehouse"
# P1 fix (v0.24.4): GOLD_FRESHNESS_MINUTES is now defined in the canonical
# schema manifest (src/lakehouse/gold_schema_manifest.py) as the single
# source of truth. The value here is kept as a fallback for the import
# path that does not load the manifest.
try:
    from src.lakehouse.gold_schema_manifest import (  # type: ignore
        GOLD_FRESHNESS_MINUTES as MANIFEST_FRESHNESS_MINUTES,
    )
    if MANIFEST_FRESHNESS_MINUTES is not None:
        GOLD_FRESHNESS_MINUTES = MANIFEST_FRESHNESS_MINUTES
    else:
        GOLD_FRESHNESS_MINUTES = 30
except Exception:
    # Manifest not importable in some test contexts.
    GOLD_FRESHNESS_MINUTES = 30
ENABLE_GOLD_PATH = True


class AsyncTrinoClient:
    def __init__(self):
        self.conn = get_trino_connection()

    async def fetch_one(self, query: str, query_type: str = "unknown"):
        def _fetch():
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor.fetchone()
        TRINO_ACTIVE_QUERIES.inc()
        t0 = time.perf_counter()
        try:
            result = await asyncio.to_thread(_fetch)
            record_trino_query(query_type, time.perf_counter() - t0, success=True)
            return result
        except Exception as e:
            record_trino_query(query_type, time.perf_counter() - t0, success=False,
                               reason=type(e).__name__)
            raise
        finally:
            TRINO_ACTIVE_QUERIES.dec()

    async def fetch_all(self, query: str, query_type: str = "unknown"):
        def _fetch():
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
        TRINO_ACTIVE_QUERIES.inc()
        t0 = time.perf_counter()
        try:
            result = await asyncio.to_thread(_fetch)
            record_trino_query(query_type, time.perf_counter() - t0, success=True)
            return result
        except Exception as e:
            record_trino_query(query_type, time.perf_counter() - t0, success=False,
                               reason=type(e).__name__)
            raise
        finally:
            TRINO_ACTIVE_QUERIES.dec()


async def get_trino():
    return AsyncTrinoClient()


@router.get("/overview")
async def get_market_overview(
    timeframe: str = Query("24h", description="Timeframe: 1h, 24h, 7d"),
    limit: int = Query(10, ge=5, le=50, description="Number of items per category")
):
    """Get comprehensive market overview with gold-first queries and Redis fallback."""
    data_sources: list[str] = []
    trino_data_available = False

    try:
        trino = await get_trino()

        market_summary = await _get_market_summary(trino)
        top_gainers = await _get_top_movers(trino, "gainer", timeframe, limit)
        top_losers = await _get_top_movers(trino, "loser", timeframe, limit)
        most_volatile = await _get_most_volatile(trino, limit)
        highest_volume = await _get_highest_volume(trino, limit)
        trending_news = await _get_trending_news(trino, limit)
        sector_performance = await _get_sector_performance(trino)
        heatmap_data = await _get_heatmap_data(trino, limit)
        indicators_summary = await _get_indicators_summary(trino)

        trino_data_available = ENABLE_GOLD_PATH and (
            market_summary.get("active_symbols", 0) > 0
            or len(top_gainers) > 0
            or len(most_volatile) > 0
            or len(highest_volume) > 0
        )

        if trino_data_available:
            data_sources.append("trino_gold")
        else:
            logger.info("Gold tables empty or stale, deriving market overview from Redis fallback")
            record_trino_fallback("market_overview", "gold_empty_or_stale")
            market_summary, top_gainers, top_losers, most_volatile, highest_volume = await _derive_market_from_redis(timeframe, limit)
            trending_news = []
            sector_performance = {}
            heatmap_data = []
            indicators_summary = {
                "total_symbols": 0,
                "avg_rsi": 50,
                "overbought_count": 0,
                "oversold_count": 0,
                "bullish_macd_count": 0,
                "bearish_macd_count": 0,
            }
            data_sources.append("redis_fallback")
    except Exception as e:
        logger.warning("Trino gold query failed (%s), falling back to Redis/ticker", e)
        record_trino_fallback("market_overview", type(e).__name__)
        market_summary, top_gainers, top_losers, most_volatile, highest_volume = await _derive_market_from_redis(timeframe, limit)
        trending_news = []
        sector_performance = {}
        heatmap_data = []
        indicators_summary = {
            "total_symbols": 0,
            "avg_rsi": 50,
            "overbought_count": 0,
            "oversold_count": 0,
            "bullish_macd_count": 0,
            "bearish_macd_count": 0,
        }
        data_sources.append("redis_fallback")

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
            "source": data_sources[0] if data_sources else "unknown",
            "data_sources": data_sources,
            "is_placeholder": "trino_gold" not in data_sources,
            "computed_at": datetime.utcnow().isoformat(),
            "gold_tables_healthy": trino_data_available,
            "warning": None if "trino_gold" in data_sources else "Fallback: data derived from live ticker Redis cache. Gold analytics unavailable or empty.",
        },
    }


async def _get_market_summary(trino) -> Dict[str, Any]:
    query = f"""
    SELECT
        COALESCE(MAX(total_volume_24h), 0) as total_volume_24h,
        COALESCE(MAX(active_symbols), 0) as active_symbols,
        COALESCE(MAX(btc_dominance_pct), 0) as btc_dominance_pct,
        COALESCE(MAX(eth_dominance_pct), 0) as eth_dominance_pct
    FROM {DB}.gold_market_dominance
    WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
    """
    result = await trino.fetch_one(query, query_type="market_summary")
    if not result:
        return {
            "total_market_cap": 0,
            "total_volume_24h": 0,
            "btc_dominance": 0,
            "eth_dominance": 0,
            "active_symbols": 0,
            "fear_greed_index": 50,
        }
    total_market_cap = 0
    return {
        "total_market_cap": float(total_market_cap),
        "total_volume_24h": float(result[0] or 0),
        "btc_dominance": float(result[2] or 0),
        "eth_dominance": float(result[3] or 0),
        "active_symbols": int(result[1] or 0),
        "fear_greed_index": 50,
    }


async def _get_top_movers(trino, category: str, timeframe: str, limit: int) -> List[Dict[str, Any]]:
    order_col = "rank_gainers" if category == "gainer" else "rank_losers"
    comparator = "> 0" if category == "gainer" else "< 0"
    query = f"""
    SELECT symbol, exchange, price, change_24h, volume_24h, {order_col}
    FROM {DB}.gold_movers_ranking
    WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
      AND change_24h {comparator}
    ORDER BY {order_col} ASC
    LIMIT {limit}
    """
    results = await trino.fetch_all(query, query_type=f"top_movers_{category}")
    return [
        {
            "symbol": row[0],
            "exchange": row[1],
            "price": round(float(row[2]), 2) if row[2] else 0,
            "change_pct": round(float(row[3]), 2) if row[3] else 0,
            "volume_24h": round(float(row[4]), 2) if row[4] else 0,
            "rank": int(row[5]) if row[5] is not None else None,
        }
        for row in results
    ]


async def _get_most_volatile(trino, limit: int) -> List[Dict[str, Any]]:
    query = f"""
    SELECT symbol, exchange, price_range_pct, atr_estimate, rank
    FROM {DB}.gold_volatility_ranking
    WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
    ORDER BY rank ASC
    LIMIT {limit}
    """
    results = await trino.fetch_all(query, query_type="most_volatile")
    return [
        {
            "symbol": row[0],
            "exchange": row[1],
            "price_range_pct": round(float(row[2]), 2) if row[2] else 0,
            "volatility_24h": round(float(row[2]), 4) if row[2] else 0,
            "atr_estimate": round(float(row[3]), 4) if row[3] else 0,
            "rank": int(row[4]) if row[4] is not None else None,
        }
        for row in results
    ]


async def _get_highest_volume(trino, limit: int) -> List[Dict[str, Any]]:
    query = f"""
    SELECT symbol, exchange, price, change_24h, volume_24h
    FROM {DB}.gold_movers_ranking
    WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
    ORDER BY volume_24h DESC
    LIMIT {limit}
    """
    results = await trino.fetch_all(query, query_type="highest_volume")
    return [
        {
            "symbol": row[0],
            "exchange": row[1],
            "price": round(float(row[2]), 2) if row[2] else 0,
            "change_pct": round(float(row[3]), 2) if row[3] else 0,
            "volume_24h": round(float(row[4]), 2) if row[4] else 0,
        }
        for row in results
    ]


async def _get_trending_news(trino, limit: int) -> List[Dict[str, Any]]:
    query = f"""
    SELECT symbol, article_count, avg_sentiment, bullish_count, bearish_count
    FROM {DB}.gold_news_sentiment_daily
    WHERE date >= current_timestamp - INTERVAL '7' DAY
    ORDER BY article_count DESC
    LIMIT {limit}
    """
    results = await trino.fetch_all(query, query_type="trending_news")
    return [
        {
            "symbol": row[0],
            "article_count": row[1],
            "avg_sentiment": round(float(row[2]), 3) if row[2] else 0,
            "sentiment_positive": row[3],
            "sentiment_negative": row[4],
        }
        for row in results
    ]


async def _get_sector_performance(trino) -> Dict[str, Any]:
    query = f"""
    SELECT sector, avg_change_pct, total_volume, symbol_count
    FROM {DB}.gold_sector_performance
    WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
    ORDER BY total_volume DESC
    LIMIT 10
    """
    results = await trino.fetch_all(query, query_type="sector_performance")
    sectors = {}
    for row in results:
        sectors[str(row[0]).lower().replace(" ", "_")] = {
            "change_pct": round(float(row[1]), 2) if row[1] else 0,
            "volume": round(float(row[2]), 2) if row[2] else 0,
            "symbol_count": row[3],
        }
    return sectors


async def _get_heatmap_data(trino, limit: int) -> List[Dict[str, Any]]:
    query = f"""
    SELECT
        m.symbol,
        m.change_24h,
        m.price,
        m.volume_24h,
        (m.price * m.volume_24h * 10) as market_cap,
        v.price_range_pct
    FROM {DB}.gold_movers_ranking m
    LEFT JOIN {DB}.gold_volatility_ranking v
        ON m.symbol = v.symbol AND m.exchange = v.exchange
    WHERE m.computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
    ORDER BY market_cap DESC
    LIMIT {limit}
    """
    results = await trino.fetch_all(query, query_type="heatmap")
    return [
        {
            "symbol": row[0],
            "change_pct": round(float(row[1]), 2) if row[1] else 0,
            "price": round(float(row[2]), 2) if row[2] else 0,
            "volume_24h": round(float(row[3]), 2) if row[3] else 0,
            "market_cap": round(float(row[4]), 2) if row[4] else 0,
            "volatility": round(float(row[5]), 4) if row[5] else 0,
        }
        for row in results
    ]


async def _get_indicators_summary(trino) -> Dict[str, Any]:
    query = f"""
    SELECT
        COUNT(*) as total_symbols,
        AVG(CASE WHEN rsi_signal = 'overbought' THEN 75 WHEN rsi_signal = 'oversold' THEN 25 ELSE 50 END) as avg_rsi,
        SUM(CASE WHEN rsi_signal = 'overbought' THEN 1 ELSE 0 END) as overbought_count,
        SUM(CASE WHEN rsi_signal = 'oversold' THEN 1 ELSE 0 END) as oversold_count,
        SUM(CASE WHEN macd_signal = 'bullish_cross' THEN 1 ELSE 0 END) as bullish_macd_count,
        SUM(CASE WHEN macd_signal = 'bearish_cross' THEN 1 ELSE 0 END) as bearish_macd_count
    FROM {DB}.gold_momentum_indicators
    WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
    """
    result = await trino.fetch_one(query, query_type="indicators_summary")
    if not result:
        return {
            "total_symbols": 0,
            "avg_rsi": 50,
            "overbought_count": 0,
            "oversold_count": 0,
            "bullish_macd_count": 0,
            "bearish_macd_count": 0,
        }
    return {
        "total_symbols": int(result[0] or 0),
        "avg_rsi": round(float(result[1]), 2) if result[1] else 50,
        "overbought_count": int(result[2] or 0),
        "oversold_count": int(result[3] or 0),
        "bullish_macd_count": int(result[4] or 0),
        "bearish_macd_count": int(result[5] or 0),
    }


async def _derive_market_from_redis(timeframe: str, limit: int):
    """Derive market overview from Redis ticker:latest scan when gold tables are unavailable."""
    from backend.core.database import get_redis
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
        exchange = key.split(":")[-2] if len(key.split(":")) >= 3 else "unknown"
        try:
            price = float(data.get("price", 0))
            volume = float(data.get("volume", 0))
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
    sorted_change = sorted(tickers, key=lambda t: t["change_pct"], reverse=True)
    top_gainers = sorted_change[:limit]
    top_losers = sorted_change[-limit:][::-1]
    for t in tickers:
        t["volatility"] = round(abs(t["change_pct"]) + t["spread"] / (t["price"] or 1) * 100, 4)
    most_volatile = sorted(tickers, key=lambda t: t["volatility"], reverse=True)[:limit]
    for t in top_gainers + top_losers + most_volatile:
        t.pop("spread", None)
    highest_volume = sorted(tickers, key=lambda t: t["volume_24h"], reverse=True)[:limit]
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
        logger.warning("heatmap endpoint failed: %s", e)
        record_trino_fallback("heatmap", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Heatmap data unavailable: {type(e).__name__}",
        )


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
        logger.warning("rankings endpoint failed: %s", e)
        record_trino_fallback(f"rankings_{category}", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Rankings data unavailable: {type(e).__name__}",
        )


# ============================================================================
# DEDICATED ENDPOINTS (Task 1, v0.24.4)
# ----------------------------------------------------------------------------
# These endpoints expose ONE gold table per call. They are designed for
# Frontend features that need a single slice of data without paying the
# cost of /overview (which queries 6 tables in one round trip).
#
# All endpoints:
# - Share ``GOLD_FRESHNESS_MINUTES`` window and Trino fallback semantics.
# - Return 503 (not 500) when Trino is unreachable and Redis fallback
#   cannot provide the slice, so clients can distinguish "down" from
#   "broken".
# - Are excluded from the heatmap/rankings/overview aggregation.
# ============================================================================


@router.get("/movers")
async def get_movers(
    category: str = Query("gainer",
                          pattern="^(gainer|loser)$",
                          description="gainer or loser"),
    limit: int = Query(20, ge=5, le=100),
):
    """Top gainers/losers from ``gold_movers_ranking``.

    Replaces the path used by the previous /rankings/{category} endpoint
    with a cleaner flat response: ``{"category", "data": [...]}``.
    """
    try:
        trino = await get_trino()
        data = await _get_top_movers(trino, category, "24h", limit)
    except Exception as e:
        logger.warning("movers endpoint failed: %s", e)
        record_trino_fallback(f"movers_{category}", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Gold data unavailable: {type(e).__name__}",
        )
    return {
        "category": category,
        "timeframe": "24h",
        "limit": limit,
        "count": len(data),
        "data": data,
        "computed_at": datetime.now().isoformat(),
    }


@router.get("/dominance")
async def get_dominance():
    """BTC/ETH dominance and market summary from ``gold_market_dominance``."""
    try:
        trino = await get_trino()
        data = await _get_market_summary(trino)
    except Exception as e:
        logger.warning("dominance endpoint failed: %s", e)
        record_trino_fallback("dominance", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Gold data unavailable: {type(e).__name__}",
        )
    return {
        "data": data,
        "computed_at": datetime.now().isoformat(),
    }


@router.get("/volatility")
async def get_volatility(
    limit: int = Query(20, ge=5, le=100),
):
    """Top volatile symbols from ``gold_volatility_ranking``."""
    try:
        trino = await get_trino()
        data = await _get_most_volatile(trino, limit)
    except Exception as e:
        logger.warning("volatility endpoint failed: %s", e)
        record_trino_fallback("volatility", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Gold data unavailable: {type(e).__name__}",
        )
    return {
        "limit": limit,
        "count": len(data),
        "data": data,
        "computed_at": datetime.now().isoformat(),
    }


@router.get("/sectors")
async def get_sectors():
    """Sector performance from ``gold_sector_performance``.

    Returns a list (not dict) so the Frontend can render directly without
    an Object.values() step.
    """
    try:
        trino = await get_trino()
        sectors_dict = await _get_sector_performance(trino)
    except Exception as e:
        logger.warning("sectors endpoint failed: %s", e)
        record_trino_fallback("sectors", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Gold data unavailable: {type(e).__name__}",
        )
    # Convert dict → list, with key preserved as 'sector' field
    data = [
        {"sector": key.replace("_", " ").title(), **value}
        for key, value in sectors_dict.items()
    ]
    return {
        "count": len(data),
        "data": data,
        "computed_at": datetime.now().isoformat(),
    }


@router.get("/news-sentiment")
async def get_news_sentiment(
    days: int = Query(7, ge=1, le=30, description="Lookback window in days"),
    limit: int = Query(20, ge=5, le=100),
):
    """News sentiment from ``gold_news_sentiment_daily``.

    Filters by ``date >= current_timestamp - INTERVAL '{days}' DAY`` and
    orders by article count DESC.
    """
    try:
        trino = await get_trino()
        query = f"""
        SELECT symbol, article_count, avg_sentiment, bullish_count, bearish_count
        FROM {DB}.gold_news_sentiment_daily
        WHERE date >= current_timestamp - INTERVAL '{days}' DAY
        ORDER BY article_count DESC
        LIMIT {limit}
        """
        results = await trino.fetch_all(query, query_type="news_sentiment")
    except Exception as e:
        logger.warning("news-sentiment endpoint failed: %s", e)
        record_trino_fallback("news_sentiment", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Gold data unavailable: {type(e).__name__}",
        )
    data = [
        {
            "symbol": row[0],
            "article_count": row[1],
            "avg_sentiment": round(float(row[2]), 3) if row[2] else 0,
            "bullish_count": row[3],
            "bearish_count": row[4],
        }
        for row in results
    ]
    return {
        "days": days,
        "limit": limit,
        "count": len(data),
        "data": data,
        "computed_at": datetime.now().isoformat(),
    }


@router.get("/indicators")
async def get_indicators():
    """Momentum / RSI / MACD summary from ``gold_momentum_indicators``."""
    try:
        trino = await get_trino()
        data = await _get_indicators_summary(trino)
    except Exception as e:
        logger.warning("indicators endpoint failed: %s", e)
        record_trino_fallback("indicators", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Gold data unavailable: {type(e).__name__}",
        )
    return {
        "data": data,
        "computed_at": datetime.now().isoformat(),
    }


# ============================================================================
# WHALE ALERTS (Task 2, v0.24.4)
# ----------------------------------------------------------------------------
# Real-time large-trade detection. The Flink writer
# (src/processing/writers/whale_alert.py) filters crypto_trades for
# notional USD >= threshold and writes to Redis sorted set
# ``whale:alerts:{exchange}:{symbol}``. This endpoint reads from Redis
# directly — no Trino, no aggregation, no falling back to a query.
# Redis 503 is the only failure mode; the response surfaces a clear
# ``redis_unavailable`` reason in that case.
#
# Query params:
#   min_usd         — minimum notional USD (default 100_000)
#   limit           — max alerts returned, sorted by trade_time DESC
#   since_minutes   — lookback window (default 60). Alerts older than
#                     this are filtered out (Redis TTL is 1h, so values
#                     above 60 are clamped down).
#   symbol          — optional filter, e.g. "BTCUSDT". Multi-symbol is
#                     not supported in v0.24.4 (use the unfiltered call
#                     and filter client-side if needed).
# ============================================================================


def _whale_alert_key(exchange: str, symbol: str) -> str:
    return f"whale:alerts:{exchange}:{symbol}"


# ============================================================================
# LIQUIDITY HEATMAP (Task 5, v0.24.5)
# ----------------------------------------------------------------------------
# Reads aggregated order-book depth buckets from the InfluxDB
# ``liquidity_heatmap`` measurement (written by
# src/processing/writers/liquidity_heatmap.py). Returns a 2-D matrix
# (time × price-bucket) per side (bid/ask) for the requested window.
#
# Query params:
#   symbol          — required, e.g. "BTCUSDT". Regex: ^[A-Z0-9]{2,20}USDT$
#   hours           — lookback window, 1..24 (default 4)
#   bucket_count    — number of price-bucket columns to return per side
#                     (default 20, max 100). Always centered on mid (=0).
#   exchange        — reference exchange (default 'binance')
#
# Response shape:
#   {
#     "data": {
#       "bid": [ [t0, b0, qty], [t0, b1, qty], ..., [tN, bM, qty] ],
#       "ask": [ ... ]
#     },
#     "matrix_shape": { "time_buckets": N, "price_buckets_per_side": M },
#     "meta": { "mid_price": X, "bucket_pct": 0.1, "exchange": "binance" }
#   }
#
# The frontend renders this as a CSS-grid heatmap. We do NOT do the
# pivoting on the server — the client pivots a flat list of
# (time, bucket, quantity) tuples into a grid.
# ============================================================================


@router.get("/liquidity-heatmap")
async def get_liquidity_heatmap(
    symbol: str = Query(
        ..., pattern=r"^[A-Z0-9]{2,20}USDT$",
        description="Symbol (canonical form, e.g. BTCUSDT)",
    ),
    hours: int = Query(4, ge=1, le=24),
    bucket_count: int = Query(20, ge=1, le=100),
    exchange: str = Query("binance", min_length=1, max_length=32),
):
    """Liquidity heatmap: quantity at each (time, price-bucket, side)."""
    from backend.core.database import get_influx
    try:
        influx = get_influx()
        query_api = influx.query_api()
    except Exception as e:
        logger.warning("liquidity-heatmap Influx init failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"InfluxDB unavailable: {type(e).__name__}",
        )

    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{int(hours)}h, stop: now())
  |> filter(fn: (r) => r._measurement == "liquidity_heatmap")
  |> filter(fn: (r) => r.symbol == "{symbol}")
  |> filter(fn: (r) => r.exchange == "{exchange}")
  |> filter(fn: (r) => r._field == "quantity")
  |> keep(columns: ["_time", "side", "price_bucket", "_value"])
  |> group(columns: ["side", "price_bucket"])
  |> sort(columns: ["_time"])
'''
    try:
        tables = query_api.query(flux)
    except Exception as e:
        logger.warning("liquidity-heatmap Influx query failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Heatmap data unavailable: {type(e).__name__}",
        )

    bid_rows: list[list] = []
    ask_rows: list[list] = []
    time_buckets: set[int] = set()

    for table in tables:
        for record in table.records:
            side = record.values.get("side")
            bucket = int(record.values.get("price_bucket", 0))
            if side == "bid" and bucket < bucket_count:
                bid_rows.append([
                    int(record.get_time().timestamp() * 1000),
                    bucket,
                    float(record.get_value()),
                ])
                time_buckets.add(int(record.get_time().timestamp() * 1000))
            elif side == "ask" and bucket < bucket_count:
                ask_rows.append([
                    int(record.get_time().timestamp() * 1000),
                    bucket,
                    float(record.get_value()),
                ])
                time_buckets.add(int(record.get_time().timestamp() * 1000))

    return {
        "data": {"bid": bid_rows, "ask": ask_rows},
        "matrix_shape": {
            "time_buckets": len(time_buckets),
            "price_buckets_per_side": bucket_count,
        },
        "filter": {
            "symbol": symbol,
            "hours": hours,
            "bucket_count": bucket_count,
            "exchange": exchange,
        },
    }


# ============================================================================
# NEWS ↔ PRICE IMPACT (Task 4, v0.24.5)
# ----------------------------------------------------------------------------
# For each news article in ``gold_news_market_impact`` we measured
# the price change at t+1h, t+4h and t+24h (see
# src/lakehouse/gold/news_impact.py). This endpoint surfaces the
# top-impactful news so a UI can render a "News Impact" panel and
# overlay markers on the candlestick chart.
#
# Query params:
#   days            — lookback window in days (default 7, max 90).
#   limit           — max rows returned (default 50, max 200).
#   symbol          — optional filter, e.g. "BTCUSDT".
#   min_impact_pct  — only return rows where ABS(impact_score) >= N.
#                     Default 0 (no filter). Useful for hiding noise.
#   exchange        — reference exchange (default 'binance'). Only one
#                     reference is stored per row in v0.24.5.
#
# Sort: by ABS(impact_score) DESC (most market-moving first).
# ============================================================================


_NEWS_IMPACT_TABLE = "iceberg.crypto_lakehouse.gold_news_market_impact"


@router.get("/news-impact")
async def get_news_impact(
    days: int = Query(7, ge=1, le=90, description="Lookback window in days"),
    limit: int = Query(50, ge=1, le=200),
    symbol: Optional[str] = Query(
        None, pattern=r"^[A-Z0-9]{2,20}USDT$",
        description="Optional single-symbol filter (canonical form, e.g. BTCUSDT)",
    ),
    min_impact_pct: float = Query(
        0.0, ge=0.0, le=100.0,
        description="Only return rows with |impact_score| >= N",
    ),
    exchange: str = Query("binance", min_length=1, max_length=32),
):
    """Top-impactful news from ``gold_news_market_impact``."""
    try:
        trino = await get_trino()
    except Exception as e:
        logger.warning("news-impact Trino init failed: %s", e)
        record_trino_fallback("news_impact", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Trino unavailable: {type(e).__name__}",
        )

    where_clauses = [
        f"published_at >= current_timestamp - INTERVAL '{int(days)}' DAY",
        f"exchange = '{exchange}'",
    ]
    if symbol:
        where_clauses.append(f"symbol = '{symbol}'")
    if min_impact_pct > 0:
        where_clauses.append(f"ABS(impact_score) >= {float(min_impact_pct)}")

    where_sql = " AND ".join(where_clauses)
    sql = f"""
        SELECT
            news_id,
            symbol,
            exchange,
            published_at,
            headline,
            url,
            source,
            sentiment,
            price_at_news,
            price_1h_after,
            price_4h_after,
            price_24h_after,
            change_1h_pct,
            change_4h_pct,
            change_24h_pct,
            impact_score,
            computed_at
        FROM {_NEWS_IMPACT_TABLE}
        WHERE {where_sql}
        ORDER BY ABS(impact_score) DESC NULLS LAST
        LIMIT {int(limit)}
    """
    try:
        raw_rows = await trino.fetch_all(sql, query_type="news_impact")
    except Exception as e:
        logger.warning("news-impact Trino query failed: %s", e)
        record_trino_fallback("news_impact", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Gold data unavailable: {type(e).__name__}",
        )

    # ``trino.fetch_all`` returns list[tuple] in column-declaration order.
    # Convert to list[dict] for the response.
    column_names = [
        "news_id", "symbol", "exchange", "published_at",
        "headline", "url", "source", "sentiment",
        "price_at_news", "price_1h_after", "price_4h_after",
        "price_24h_after", "change_1h_pct", "change_4h_pct",
        "change_24h_pct", "impact_score", "computed_at",
    ]
    data: list[dict] = []
    for row in raw_rows:
        item = {}
        for col, val in zip(column_names, row):
            if col in ("published_at", "computed_at") and val is not None and not isinstance(val, str):
                val = str(val)
            item[col] = val
        data.append(item)

    return {
        "data": data,
        "count": len(data),
        "filter": {
            "days": days,
            "limit": limit,
            "symbol": symbol,
            "min_impact_pct": min_impact_pct,
            "exchange": exchange,
        },
    }


@router.get("/whale-alerts")
async def get_whale_alerts(
    min_usd: float = Query(100_000, ge=1_000, le=100_000_000,
                           description="Minimum notional USD"),
    limit: int = Query(20, ge=1, le=200),
    since_minutes: int = Query(60, ge=1, le=60,
                               description="Lookback in minutes; clamped to 60"),
    symbol: str | None = Query(None, description="Filter by symbol, e.g. BTCUSDT"),
    exchange: str = Query("binance", description="Exchange filter"),
):
    """Real-time whale alerts (large trades >= min_usd).

    Reads ``whale:alerts:{exchange}:{symbol}`` Redis sorted sets and
    returns the most recent alerts, newest first. Each alert is a JSON
    blob produced by the Flink ``WhaleAlertWriter``.

    Note: ``since_minutes`` is clamped to 60 (Redis TTL). To query
    older alerts, use the InfluxDB ``whale_alerts`` measurement
    directly (out of scope for v0.24.4).
    """
    from backend.core.database import get_redis

    # Clamp lookback to Redis TTL
    since_minutes = min(since_minutes, 60)
    cutoff_ms = int((time.time() - since_minutes * 60) * 1000)

    try:
        r = await get_redis()
    except Exception as e:
        logger.warning("whale-alerts: redis client init failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Redis unavailable: {type(e).__name__}",
        )

    # Determine which keys to scan
    if symbol:
        keys = [_whale_alert_key(exchange, symbol)]
    else:
        # Scan all whale:alerts:*:{symbol} keys (any exchange)
        keys = []
        cursor = 0
        try:
            while True:
                cursor, batch = await r.scan(
                    cursor, match=f"whale:alerts:{exchange}:*", count=200,
                )
                keys.extend(batch)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning("whale-alerts: redis SCAN failed: %s", e)
            raise HTTPException(
                status_code=503,
                detail=f"Redis SCAN failed: {type(e).__name__}",
            )

    if not keys:
        return {
            "count": 0,
            "data": [],
            "min_usd": min_usd,
            "since_minutes": since_minutes,
            "filter": {"exchange": exchange, "symbol": symbol},
            "computed_at": datetime.now().isoformat(),
        }

    # Pull the most recent ``limit`` alerts across all matching keys.
    # We ZRANGEBYSCORE with REV + LIMIT to avoid loading the full
    # sorted set (which can hold up to 1000 entries per symbol).
    all_alerts: list[dict] = []
    try:
        for key in keys:
            # Newest first, within the freshness window
            members = await r.zrevrangebyscore(
                key, max="+inf", min=cutoff_ms,
                start=0, num=limit,
            )
            for m in members:
                try:
                    payload = json.loads(m)
                except (ValueError, TypeError):
                    continue
                # Apply min_usd filter (in case Redis has older
                # alerts written with a lower threshold)
                if float(payload.get("notional_usd", 0)) < min_usd:
                    continue
                all_alerts.append(payload)
    except Exception as e:
        logger.warning("whale-alerts: redis ZRANGE failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Redis ZRANGE failed: {type(e).__name__}",
        )

    # Sort by trade_time DESC and slice to ``limit``
    all_alerts.sort(key=lambda a: a.get("trade_time", 0), reverse=True)
    top = all_alerts[:limit]

    return {
        "count": len(top),
        "data": top,
        "min_usd": min_usd,
        "since_minutes": since_minutes,
        "filter": {"exchange": exchange, "symbol": symbol},
        "computed_at": datetime.now().isoformat(),
        "warning": (
            "Older alerts (>60min) are not in Redis. Use the InfluxDB "
            "whale_alerts measurement for historical queries."
        ) if since_minutes >= 60 else None,
    }
