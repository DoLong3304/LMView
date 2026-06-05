"""
WebSocket streaming API for real-time candle updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.constants import INTERVAL_SECONDS
from backend.core.database import get_redis

router = APIRouter(prefix="/api", tags=["websocket"])
log = logging.getLogger(__name__)

# All timeframes to stream simultaneously
ALL_INTERVALS = ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"]



@router.websocket("/stream/{interval}")
async def stream_interval(
    websocket: WebSocket,
    interval: str,
    symbol: str = "",
    exchange: str = "binance",
):
    """Real-time candle streaming for a single timeframe.

    Frontend connects with:
        ``ws://host/api/stream/1m?symbol=BTCUSDT&exchange=binance``

    Returns JSON with the latest candle for the requested interval.
    """
    interval = interval.strip().lower()
    if interval not in ALL_INTERVALS:
        await websocket.accept()
        await websocket.send_json({"error": f"Unsupported interval: {interval}"})
        await websocket.close()
        return

    await websocket.accept()
    r = await get_redis()
    symbol = symbol.upper()
    exchange = exchange.strip().lower() or "binance"
    target_ms = INTERVAL_SECONDS[interval] * 1000
    last_sent = None

    try:
        while True:
            ticker = await r.hgetall(f"ticker:latest:{exchange}:{symbol}")
            live_price = float(ticker["price"]) if ticker.get("price") else None
            live_ts = int(ticker["event_time"]) if ticker.get("event_time") else None

            candle = await _build_candle(
                r, symbol, interval, target_ms, exchange, live_price, live_ts,
            )
            if candle and candle != last_sent:
                await websocket.send_json(candle)
                last_sent = candle

            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("Stream %s error for %s: %s", interval, symbol, e)


@router.websocket("/stream/indicators/{interval}")
async def stream_indicators(
    websocket: WebSocket,
    interval: str,
    symbol: str = "",
    exchange: str = "binance",
):
    """Real-time indicator snapshot streaming for a single timeframe."""
    interval = interval.strip().lower()
    if interval not in ALL_INTERVALS:
        await websocket.accept()
        await websocket.send_json({"error": f"Unsupported interval: {interval}"})
        await websocket.close()
        return

    await websocket.accept()
    r = await get_redis()
    symbol = symbol.upper()
    exchange = exchange.strip().lower() or "binance"
    last_sent = None

    try:
        while True:
            payload = await _build_indicator_snapshot(r, symbol, exchange, interval)
            if payload and payload != last_sent:
                await websocket.send_json(payload)
                last_sent = payload

            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("Indicator stream %s error for %s: %s", interval, symbol, e)


@router.websocket("/stream/all")
async def stream_all(websocket: WebSocket, symbol: str = "", exchange: str = "binance"):
    """
    Real-time candle streaming for ALL timeframes simultaneously via a single WebSocket.

    The frontend connects with:
        ``ws://host/api/stream/all?symbol=BTCUSDT&exchange=binance``

    Returns JSON with shape:
        {
          "1s": { candle },
          "1m": { candle },
          "5m": { candle },
          ...
        }
    """
    await websocket.accept()
    r = await get_redis()
    symbol = symbol.upper()
    exchange = exchange.strip().lower() or "binance"

    # Build target_ms lookup
    target_ms_map = {iv: INTERVAL_SECONDS[iv] * 1000 for iv in ALL_INTERVALS}
    last_sent: dict[str, dict | None] = {iv: None for iv in ALL_INTERVALS}

    try:
        while True:
            result: dict[str, dict | None] = {}
            any_changed = False

            # Fetch ticker ONCE for all intervals (avoid N+1 queries)
            ticker = await r.hgetall(f"ticker:latest:{exchange}:{symbol}")
            live_price = float(ticker["price"]) if ticker.get("price") else None
            live_ts = int(ticker["event_time"]) if ticker.get("event_time") else None

            # Only build timeframes that have actually changed (delta updates)
            for iv in ALL_INTERVALS:
                # Fetch candle without redundant hgetall calls
                candle = await _build_candle(r, symbol, iv, target_ms_map[iv], exchange, live_price, live_ts)
                if candle and candle != last_sent[iv]:
                    result[iv] = candle
                    last_sent[iv] = candle
                    any_changed = True
                else:
                    result[iv] = last_sent[iv]

            # Only send if something changed
            if any_changed:
                await websocket.send_json(result)

            # CRITICAL: Reduced from 0.3s to 0.05s for real-time responsiveness
            # This is the primary latency source — tighter loop = faster updates
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("Stream all error for %s: %s", symbol, e)


async def _build_candle(
    r,
    symbol: str,
    interval: str,
    target_ms: int,
    exchange: str = "binance",
    live_price: float | None = None,
    live_ts: int | None = None,
) -> dict | None:
    """Build the latest candle by merging Flink aggregate data with the
    real-time ticker price.

    OPTIMIZATION: Caller MUST provide live_price and live_ts (pre-fetched)
    to avoid redundant Redis hgetall calls. If not provided, fetch once.
    """

    # If not pre-fetched, fetch once (but caller should provide these)
    if live_price is None or live_ts is None:
        ticker = await r.hgetall(f"ticker:latest:{exchange}:{symbol}")
        live_price = live_price or (float(ticker["price"]) if ticker.get("price") else None)
        live_ts = live_ts or (int(ticker["event_time"]) if ticker.get("event_time") else None)

    # 1s interval: serve directly from KeyDB
    if interval == "1s":
        raw = await r.zrevrange(f"candle:1s:{exchange}:{symbol}", 0, 0)
        if raw:
            c = json.loads(raw[0])
            return {
                "openTime": int(c["t"]),
                "open": c["o"], "high": c["h"],
                "low": c["l"], "close": c["c"],
                "volume": c["v"],
            }
        return None

    # 1m+: aggregate from the appropriate source sorted set
    # KeyDB stores candles with exchange prefix: candle:1s:binance:BTCUSDT
    source_key = f"candle:1s:{exchange}:{symbol}" if interval == "1m" else f"candle:1m:{exchange}:{symbol}"
    latest = await r.zrevrange(source_key, 0, 0, withscores=True)

    flink_candle = None
    flink_window = 0
    latest_source_ts = 0
    if latest:
        latest_score = int(latest[0][1])
        flink_window = (latest_score // target_ms) * target_ms
        raw = await r.zrangebyscore(
            source_key, flink_window, flink_window + target_ms - 1,
        )
        if raw:
            candles = [json.loads(c) for c in raw]
            latest_source_ts = max(int(c["t"]) for c in candles)
            flink_candle = {
                "openTime": flink_window,
                "open": candles[0]["o"],
                "high": max(c["h"] for c in candles),
                "low": min(c["l"] for c in candles),
                "close": candles[-1]["c"],
                "volume": round(sum(c["v"] for c in candles), 8),
            }

    # Keep 1m candles exchange-consistent: no ticker-based override
    if interval == "1m":
        return flink_candle

    # Merge with real-time ticker for 5m+ only
    if live_price and live_ts:
        live_window = (live_ts // target_ms) * target_ms
        if flink_candle and live_window == flink_window:
            window_close_ms = flink_window + target_ms
            if live_ts > latest_source_ts and int(time.time() * 1000) < window_close_ms:
                flink_candle["close"] = live_price
                flink_candle["high"] = max(flink_candle["high"], live_price)
                flink_candle["low"] = min(flink_candle["low"], live_price)
            return flink_candle
        if live_window > flink_window:
            return {
                "openTime": live_window,
                "open": live_price, "high": live_price,
                "low": live_price, "close": live_price,
                "volume": 0,
            }

    if flink_candle:
        return flink_candle

    # Last resort fallback
    data = await r.hgetall(f"candle:latest:{exchange}:{symbol}")
    if data:
        kline_start = int(data["kline_start"])
        return {
            "openTime": (kline_start // target_ms) * target_ms,
            "open": float(data["open"]),
            "high": float(data["high"]),
            "low": float(data["low"]),
            "close": float(data["close"]),
            "volume": float(data["volume"]),
        }
    return None


async def _build_indicator_snapshot(
    r,
    symbol: str,
    exchange: str,
    interval: str,
) -> dict | None:
    """Read latest indicator snapshot from Redis and normalize the payload."""
    data = await r.hgetall(f"indicator:latest:{exchange}:{symbol}:{interval}")
    if not data:
        data = await r.hgetall(f"indicator:latest:{exchange}:{symbol}")
    if not data:
        data = await r.hgetall(f"indicator:latest:{symbol}")
    if not data:
        return None

    timestamp = None
    if data.get("timestamp"):
        try:
            timestamp = int(float(data["timestamp"]))
        except (TypeError, ValueError):
            timestamp = None

    indicators = {}
    for key, raw_value in data.items():
        if key in {"timestamp", "interval"}:
            continue
        try:
            indicators[key] = float(raw_value)
        except (TypeError, ValueError):
            continue

    return {
        "symbol": symbol,
        "exchange": exchange,
        "interval": data.get("interval", interval),
        "timestamp": timestamp,
        "indicators": indicators,
    }
