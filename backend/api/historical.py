"""
Historical Klines API — cold storage queries for date-range OHLCV data.

Thin route handler that delegates business logic to candle_service.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from backend.core.constants import INTERVAL_SECONDS, MAX_RAW_ROWS
from backend.services.candle_service import (
    validate_symbol,
    validate_interval,
    aggregate,
    merge_unique,
    query_influx_1m_range,
    query_trino_1m,
    query_trino_hourly,
)

router = APIRouter(prefix="/api", tags=["historical"])
logger = logging.getLogger(__name__)


@router.get("/klines/historical")
async def get_historical_klines(
    symbol: str,
    interval: str = Query("1h", description="Target interval (1m/5m/15m/1h/4h/1d/1w)"),
    startTime: int = Query(..., description="Range start in epoch milliseconds"),
    endTime: int = Query(..., description="Range end in epoch milliseconds"),
    limit: int = Query(500, ge=1, le=5000),
):
    """
    Query cold storage for historical OHLCV candles within a specific date range.
    All higher intervals are derived from 1m base candles.
    """
    symbol = validate_symbol(symbol)
    interval, target_sec = validate_interval(interval)

    if endTime <= startTime:
        raise HTTPException(400, "endTime must be greater than startTime")

    max_range_ms = 365 * 24 * 3600 * 1000
    if endTime - startTime > max_range_ms:
        raise HTTPException(400, "Date range cannot exceed 1 year")

    mult = max(target_sec // 60, 1)
    raw_limit = min((limit * mult) + mult, MAX_RAW_ROWS)
    candles: list[dict] = []

    # InfluxDB is the first historical source even for old timestamps.
    # Backfill jobs can load arbitrary dates into the `crypto_ticker` bucket;
    # restricting Influx to the nominal 90d retention window caused 2025
    # backfilled candles to be skipped, returning empty results despite data
    # being available through the normal `/api/klines` fallback chain.
    try:
        influx_rows = await asyncio.to_thread(
            query_influx_1m_range, symbol, startTime, endTime, raw_limit,
        )
        candles = merge_unique(candles, influx_rows)
    except Exception as exc:
        logger.warning(
            "Historical Influx 1m query failed for %s [%s,%s): %s",
            symbol,
            startTime,
            endTime,
            exc,
        )

    # Iceberg/S3 via Trino remains cold-storage fallback when Influx lacks
    # requested rows or only partially covers the range.
    required_raw = min(raw_limit, max(limit * mult, limit))
    if len(candles) < required_raw:
        try:
            trino_rows = await asyncio.to_thread(
                query_trino_1m, symbol, endTime, raw_limit, start_ms=startTime,
            )
            candles = merge_unique(candles, trino_rows)
        except Exception as exc:
            logger.warning(
                "Historical Trino 1m query failed for %s [%s,%s): %s",
                symbol,
                startTime,
                endTime,
                exc,
            )

    # No 1m data → fallback to hourly cold table for 1h+
    if not candles:
        if interval in ("1m", "5m", "15m"):
            return []
        hourly_limit = min(max(limit * max(target_sec // 3600, 1), limit), 5000)
        candles = await asyncio.to_thread(
            query_trino_hourly, symbol, endTime, hourly_limit, start_ms=startTime,
        )
        if candles and interval in ("4h", "1d", "1w"):
            candles = aggregate(candles, target_sec * 1000)
        candles = [c for c in candles if startTime <= c["openTime"] < endTime]
        return candles[-limit:]

    if interval != "1m":
        candles = aggregate(candles, target_sec * 1000)
    candles = [c for c in candles if startTime <= c["openTime"] < endTime]
    return candles[-limit:]
