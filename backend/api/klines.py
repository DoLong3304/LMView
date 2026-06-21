"""
Klines API — real-time and recent OHLCV candle data.

Thin route handler that delegates business logic to candle_service.
"""

from __future__ import annotations

import asyncio
import json
import time

from typing import List

from backend.core.constants import INTERVAL_SECONDS, INFLUX_1M_RETENTION_DAYS, MAX_RAW_CANDLES, LIVE_MAX_BASE_ROWS, MAX_BACKFILL_PAGES
from backend.core.database import get_redis
from backend.core.redis_sentinel import get_redis_master
from backend.services.candle_service import (
    validate_symbol,
    validate_interval,
    aggregate,
    merge_unique,
    collect_base_1m_candles,
    query_influx_candles,
    query_trino_hourly,
)

from fastapi import APIRouter, Query
router = APIRouter(prefix="/api", tags=["klines"])

# New merged endpoint
from fastapi import Depends
from typing import Dict
from backend.core.database import get_redis


@router.get("/klines")
async def get_klines(
    symbol: str,
    interval: str = "1m",
    limit: int = Query(200, ge=1, le=1500),
    endTime: int | None = Query(None, description="End timestamp in milliseconds (exclusive). If provided, returns candles before this time."),
    exchange: str = Query("binance", description="Exchange name (e.g. binance)"),
):
    """
    Historical OHLCV candles.

    If endTime is provided, returns `limit` candles ending before endTime (useful for scroll loading).
    """
    symbol = validate_symbol(symbol)
    interval, target_sec = validate_interval(interval)
    exchange = exchange.strip().lower() or "binance"

    r = await get_redis()
    cache_key = f"klines_cache:{exchange}:{symbol}:{interval}:{limit}"

    # Check Redis cache (skip for scroll queries)
    if not endTime:
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)

    candles = []
    now_ms = int(time.time() * 1000)
    influx_cutoff_ms = now_ms - (INFLUX_1M_RETENTION_DAYS * 24 * 3600 * 1000)

    if interval == "1s":
        candles = await _fetch_1s_candles(r, symbol, limit, endTime, now_ms, exchange)
    elif interval == "1m" and endTime is None:
        candles = await _fetch_best_1m_candles(r, symbol, limit, now_ms, exchange)
    else:
        candles = await _fetch_1m_plus_candles(
            r, symbol, interval, target_sec, limit, endTime, now_ms, influx_cutoff_ms, exchange,
        )

    # Aggregate for intervals above 1-minute resolution
    if interval not in ("1s", "1m") and candles:
        candles = aggregate(candles, target_sec * 1000)

    # Build final result
    if endTime:
        candles = [c for c in candles if c["openTime"] < endTime]
        result = candles[-limit:] if candles else []
    else:
        if interval not in ("1s", "1m"):
            candles = await _enrich_with_live_ticker(r, symbol, target_sec, candles, exchange)
        result = candles[-limit:]

    # Cache result (skip for scroll queries)
    if not endTime:
        ttl_ms = 200 if interval == "1s" else 1500
        # Use master for write operations
        r_master = await get_redis_master()
        pipe = r_master.pipeline()
        pipe.set(cache_key, json.dumps(result))
        pipe.pexpire(cache_key, ttl_ms)
        await pipe.execute()

    return result

# Merged endpoint
from fastapi import Depends
from typing import Dict, List
from redis.asyncio import Redis

@router.get("/merged/{symbol}")
async def get_merged_klines(
    symbol: str,
    interval: str = "1m",
    limit: int = Query(100, ge=1, le=1000),
    redis: Redis = Depends(get_redis),
) -> List[Dict]:
    """Return merged candles: closed candles from Redis zset + live forming candle."""
    # 1. Get closed candles (most recent first)
    zset_key = f"candle:{interval}:binance:{symbol.lower()}"
    raw = await redis.zrevrangebyscore(zset_key, "+inf", "-inf", withscores=True, start=0, num=limit)
    closed: List[Dict] = []
    for item_bytes, ts_ms in raw:
        item = json.loads(item_bytes)
        item["isClosed"] = True
        item["timestamp"] = int(ts_ms)
        closed.append(item)

    # 2. Get live ticker
    ticker_key = f"ticker:latest:binance:{symbol.lower()}"
    ticker = await redis.hgetall(ticker_key)
    if not ticker:
        return closed
    current_price = float(ticker.get(b"price", 0) or 0)
    current_ts = int(ticker.get(b"event_time", int(time.time() * 1000)))
    if current_price <= 0:
        return closed
    forming_ts = (current_ts // 60000) * 60000
    # 3. Build forming candle
    if closed and closed[0]["timestamp"] == forming_ts:
        last = closed[0]
        forming = {
            "timestamp": forming_ts,
            "open": last["open"],
            "high": max(last["high"], current_price),
            "low": min(last["low"], current_price),
            "close": current_price,
            "volume": last["volume"],
            "quote_volume": last.get("quote_volume", 0),
            "trade_count": last.get("trade_count", 0),
            "isClosed": False,
        }
        merged = [forming] + closed[1:]
    elif closed:
        forming = {
            "timestamp": forming_ts,
            "open": current_price,
            "high": current_price,
            "low": current_price,
            "close": current_price,
            "volume": 0,
            "quote_volume": 0,
            "trade_count": 0,
            "isClosed": False,
        }
        merged = [forming] + closed
    else:
        forming = {
            "timestamp": forming_ts,
            "open": current_price,
            "high": current_price,
            "low": current_price,
            "close": current_price,
            "volume": 0,
            "quote_volume": 0,
            "trade_count": 0,
            "isClosed": False,
        }
        merged = [forming]
    return merged


async def _fetch_1s_candles(r, symbol: str, limit: int, end_time: int | None, now_ms: int, exchange: str = "binance") -> list[dict]:
    """Fetch 1-second candles exclusively from KeyDB (speed layer)."""
    needed_1s = min(limit + 2, MAX_RAW_CANDLES)
    live_lookback_ms = max(needed_1s * 1000, 120_000)
    score_min = (end_time - needed_1s * 1000) if end_time else str(now_ms - live_lookback_ms)
    score_max = (end_time - 1) if end_time else "+inf"
    raw = await r.zrangebyscore(f"candle:1s:{exchange}:{symbol}", score_min, score_max)
    if not raw and not end_time:
        raw = await r.zrevrange(f"candle:1s:{exchange}:{symbol}", 0, needed_1s - 1)

    best_by_time: dict[int, dict] = {}
    for item in raw if raw else []:
        c = json.loads(item)
        t = int(c["t"])
        if t not in best_by_time or c["v"] > best_by_time[t]["v"]:
            best_by_time[t] = c

    candles = []
    for t, c in best_by_time.items():
        candles.append({
            "openTime": t,
            "open": c["o"], "high": c["h"],
            "low": c["l"], "close": c["c"],
            "volume": c["v"],
        })
    candles.sort(key=lambda x: x["openTime"])
    return candles


async def _fetch_1m_plus_candles(
    r, symbol: str, interval: str, target_sec: int, limit: int,
    end_time: int | None, now_ms: int, influx_cutoff_ms: int, exchange: str = "binance",
) -> list[dict]:
    """Fetch 1m+ candles from KeyDB → InfluxDB → Trino fallback.

    Sources, in priority order:
      1. candle:1m:{exchange}:{symbol}      (live 7d writer)
      2. candle:1m:90d:{exchange}:{symbol}  (90d backfill writer)
      3. InfluxDB (90d)
      4. Trino hourly (1h+ only, when 1m is sparse)
    """
    candles: list[dict] = []

    if end_time is not None:
        # Historical scroll-left: read from both 7d and 90d KeyDB namespaces,
        # then fall back to InfluxDB/Trino if still short.
        raw_needed = min((limit * max(target_sec // 60, 1)) + 2, MAX_RAW_CANDLES)

        # Step 1: 7d namespace (newest portion of the window)
        keydb_7d = await _fetch_keydb_1m_window(r, symbol, end_time, raw_needed, exchange)
        candles = merge_unique(candles, keydb_7d)

        # Step 2: 90d namespace (older portion of the window)
        keydb_90d = await _fetch_keydb_90d_window(r, symbol, end_time, raw_needed, exchange)
        candles = merge_unique(candles, keydb_90d)

        # Step 3: If still not enough, fallback to InfluxDB → Trino
        if len(candles) < limit:
            backfilled = await asyncio.to_thread(
                collect_base_1m_candles,
                symbol, target_sec, limit, end_time, now_ms, influx_cutoff_ms,
                MAX_BACKFILL_PAGES, True,
            )
            candles = merge_unique(candles, backfilled)
    else:
        # Live mode: Read from KeyDB first (speed layer, 7 days retention)
        raw_needed = min((limit * max(target_sec // 60, 1)) + 2, MAX_RAW_CANDLES)

        # Step 1: Try KeyDB candle:1m (fastest, 7 days)
        keydb_candles = await _fetch_keydb_1m(r, symbol, raw_needed, now_ms, exchange)
        candles = merge_unique(candles, keydb_candles)

        # Step 2: If not enough, fallback to InfluxDB (90 days)
        if len(candles) < limit:
            live_limit = min(max(raw_needed, limit), LIVE_MAX_BASE_ROWS)
            live_range_h = min(max((live_limit * 60) // 3600 + 2, 1), INFLUX_1M_RETENTION_DAYS * 24)
            live_rows = await asyncio.to_thread(
                query_influx_candles, symbol, "1m", live_limit, live_range_h, None,
            )
            candles = merge_unique(candles, live_rows)

    # Fallback to legacy hourly for 1h+ when 1m data is sparse
    if end_time is not None and interval in ("1h", "4h", "1d", "1w"):
        target_h = max(target_sec // 3600, 1)
        hourly_needed = min((limit * target_h) + target_h, 5000)
        if len(candles) < max(limit, target_h * 8):
            hourly_rows = await asyncio.to_thread(
                query_trino_hourly, symbol, end_time or now_ms, hourly_needed,
            )
            candles = merge_unique(candles, hourly_rows)

    return candles


async def _fetch_keydb_1m_window(
    r, symbol: str, end_ms: int, limit: int, exchange: str = "binance",
) -> list[dict]:
    """Read up to `limit` candles from candle:1m:{exchange}:{symbol} with openTime < end_ms."""
    if end_ms is None:
        return []
    raw = await r.zrevrangebyscore(
        f"candle:1m:{exchange}:{symbol}",
        end_ms - 1, "-inf", withscores=False, start=0, num=limit,
    )
    return _parse_keydb_1m(raw)


async def _fetch_keydb_90d_window(
    r, symbol: str, end_ms: int, limit: int, exchange: str = "binance",
) -> list[dict]:
    """Read up to `limit` candles from candle:1m:90d:{exchange}:{symbol} with openTime < end_ms."""
    if end_ms is None:
        return []
    raw = await r.zrevrangebyscore(
        f"candle:1m:90d:{exchange}:{symbol}",
        end_ms - 1, "-inf", withscores=False, start=0, num=limit,
    )
    return _parse_keydb_1m(raw)


def _parse_keydb_1m(raw: list[bytes] | list[str]) -> list[dict]:
    """Parse the JSON-serialized candles stored by the live/90d writers."""
    out: list[dict] = []
    for item in raw or []:
        try:
            c = json.loads(item)
        except (ValueError, TypeError):
            continue
        out.append({
            "openTime": int(c["t"]),
            "open": c["o"],
            "high": c["h"],
            "low": c["l"],
            "close": c["c"],
            "volume": c["v"],
            "quote_volume": c.get("qv", 0),
            "trade_count": c.get("n", 0),
            "is_closed": c.get("x", True),
        })
    return sorted(out, key=lambda x: x["openTime"])


async def _fetch_best_1m_candles(r, symbol: str, limit: int, now_ms: int, exchange: str = "binance") -> list[dict]:
    """Fetch 1m candles from Redis and InfluxDB, then pick the cleaner source."""
    raw_needed = min(limit + 2, MAX_RAW_CANDLES)
    keydb_candles = await _fetch_keydb_1m(r, symbol, raw_needed, now_ms, exchange)

    live_limit = min(max(raw_needed, limit), LIVE_MAX_BASE_ROWS)
    live_range_h = min(max((live_limit * 60) // 3600 + 2, 1), INFLUX_1M_RETENTION_DAYS * 24)
    influx_candles = await asyncio.to_thread(
        query_influx_candles, symbol, "1m", live_limit, live_range_h, None,
    )

    keydb_score = _score_candle_quality(keydb_candles, 60_000, limit, now_ms)
    influx_score = _score_candle_quality(influx_candles, 60_000, limit, now_ms)
    return influx_candles if influx_score > keydb_score else keydb_candles


def _score_candle_quality(candles: list[dict], interval_ms: int, limit: int, now_ms: int) -> float:
    if not candles:
        return 0.0

    candles = sorted(candles, key=lambda c: c["openTime"])[-limit:]
    valid = 0
    nonzero_volume = 0
    continuous = 0

    previous_time = None
    for c in candles:
        try:
            o = float(c["open"])
            h = float(c["high"])
            l = float(c["low"])
            close = float(c["close"])
            v = float(c.get("volume", 0))
        except (TypeError, ValueError, KeyError):
            continue

        if h >= max(o, close) and l <= min(o, close) and h >= l and all(x > 0 for x in (o, h, l, close)):
            valid += 1
        if v > 0:
            nonzero_volume += 1
        if previous_time is not None and int(c["openTime"]) - previous_time == interval_ms:
            continuous += 1
        previous_time = int(c["openTime"])

    count = len(candles)
    coverage = min(count / max(limit, 1), 1.0)
    continuity = continuous / max(count - 1, 1)
    validity = valid / count
    volume_quality = nonzero_volume / count
    age_ms = max(0, now_ms - int(candles[-1]["openTime"]))
    freshness = max(0.0, 1.0 - (age_ms / (interval_ms * 5)))

    return coverage * 40 + continuity * 25 + validity * 20 + volume_quality * 10 + freshness * 5


async def _fetch_keydb_1m(r, symbol: str, limit: int, now_ms: int, exchange: str = "binance") -> list[dict]:
    """Fetch 1-minute candles from KeyDB (speed layer, 7 days retention)."""
    # KeyDB stores last 7 days of 1m candles
    lookback_ms = min(limit * 60 * 1000, 7 * 24 * 3600 * 1000)  # Max 7 days
    score_min = now_ms - lookback_ms
    score_max = "+inf"

    raw = await r.zrangebyscore(f"candle:1m:{exchange}:{symbol}", score_min, score_max)
    if not raw:
        # Fallback: get last N candles regardless of time
        raw = await r.zrevrange(f"candle:1m:{exchange}:{symbol}", 0, limit - 1)

    best_by_time: dict[int, dict] = {}
    for item in raw if raw else []:
        c = json.loads(item)
        t = int(c["t"])
        if t not in best_by_time or c["v"] > best_by_time[t]["v"]:
            best_by_time[t] = c

    candles = []
    for t, c in best_by_time.items():
        candles.append({
            "openTime": t,
            "open": c["o"], "high": c["h"],
            "low": c["l"], "close": c["c"],
            "volume": c["v"],
        })
    candles.sort(key=lambda x: x["openTime"])
    return candles


async def _enrich_with_live_ticker(r, symbol: str, target_sec: int, candles: list[dict], exchange: str = "binance") -> list[dict]:
    """Enrich the latest candle with live ticker price for 5m+ intervals.

    Only enriches if ticker is fresher than the latest sub-candle data.
    """
    ticker = await r.hgetall(f"ticker:latest:{exchange}:{symbol}")
    if not (ticker.get("price") and ticker.get("event_time")):
        return candles

    target_ms = target_sec * 1000
    live_price = float(ticker["price"])
    live_ts = int(ticker["event_time"])
    aligned_time = (live_ts // target_ms) * target_ms
    latest_candle_ts = candles[-1]["openTime"] if candles else 0
    window_is_open = int(time.time() * 1000) < (aligned_time + target_ms)

    # Check ticker freshness against sub-candle data
    # For aggregated intervals (5m+), verify ticker is newer than source data
    if candles and candles[-1]["openTime"] == aligned_time and window_is_open:
        # Query the latest sub-candle timestamp for this window
        source_interval = "1m"  # 5m+ intervals aggregate from 1m
        source_key = f"candle:{source_interval}:{exchange}:{symbol}"
        latest_sub = await r.zrevrange(source_key, 0, 0, withscores=True)

        latest_sub_ts = 0
        if latest_sub:
            latest_sub_ts = int(latest_sub[0][1])  # score = kline_start timestamp

        # Only enrich if ticker is fresher than latest sub-candle
        if live_ts > max(latest_candle_ts, latest_sub_ts):
            candles[-1]["close"] = live_price
            candles[-1]["high"] = max(candles[-1]["high"], live_price)
            candles[-1]["low"] = min(candles[-1]["low"], live_price)
        return candles

    # Create new candle if ticker is for a newer window
    if not candles or aligned_time > candles[-1]["openTime"]:
        candles.append({
            "openTime": aligned_time,
            "open": live_price,
            "high": live_price,
            "low": live_price,
            "close": live_price,
            "volume": 0.0,
        })

    return candles
