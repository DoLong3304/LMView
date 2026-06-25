"""
WebSocket streaming API for real-time candle updates.

Instrumentation note: every route now records the new application-level
metrics defined in ``backend.api.metrics`` (connection lifecycle, message
push, multi-source fallback, slow-client buffer).  The custom counters
complement the HTTP-level ones from ``prometheus-fastapi-instrumentator``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.api.metrics import (
    record_ws_connection,
    record_ws_connection_error,
    record_ws_disconnect,
    record_ws_message_push,
    record_ws_noop,
    record_source_lookup,
    record_source_chain_outcome,
    record_ws_loop_cycle,
    record_source_freshness,
)
from backend.core.constants import INTERVAL_SECONDS
from backend.core.database import get_redis

router = APIRouter(prefix="/api", tags=["websocket"])
log = logging.getLogger(__name__)

# All timeframes to stream simultaneously
ALL_INTERVALS = ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"]

# Real-time candle cache: tracks high/low for current forming candle across
# WebSocket iterations. Reset on minute boundary or when Flink writes a new
# candle. Key = f"{exchange}:{symbol}:{interval}"
_rt_candle_cache: dict[str, dict] = {}


@router.websocket("/stream/all")
async def stream_all_first(websocket: WebSocket, symbol: str = "", exchange: str = "binance"):
    """Real-time candle streaming for all timeframes.

    This route must be registered before `/stream/{interval}` because FastAPI
    matches WebSocket routes in declaration order.
    """
    await _stream_all_impl(websocket, symbol, exchange)


async def stream_all(websocket: WebSocket):
    """
    Real-time candle streaming for ALL timeframes simultaneously via a single WebSocket.

    Returns JSON with shape: { "1s": { candle }, "1m": { candle }, "5m": { candle }, ... }

    Real-time source: trade stream (every ~100ms) drives candle updates.
    Historical candles come from 1s/1m Redis sorted sets.
    """
    await websocket.accept()
    r = await get_redis()
    symbol = websocket.query_params.get("symbol", "BTCUSDT").upper()
    exchange = websocket.query_params.get("exchange", "binance").strip().lower() or "binance"
    record_ws_connection(route="/stream/all_legacy", accepted=True)
    connect_time = time.monotonic()

    target_ms_map = {iv: INTERVAL_SECONDS[iv] * 1000 for iv in ALL_INTERVALS}

    # Pre-build Redis keys
    ticker_key = f"ticker:latest:{exchange}:{symbol}"
    candle_1s_key = f"candle:1s:{exchange}:{symbol}"
    candle_1m_key = f"candle:1m:{exchange}:{symbol}"
    trade_key = f"trade:latest:{exchange}:{symbol}"

    # Real-time candle state (updated from trade stream)
    rt_candles: dict[str, dict] = {}

    # Track last trade to detect changes
    last_trade_ts: int = 0
    last_trade_price: float = 0

    try:
        while True:
            cycle_start = time.monotonic()
            # Fetch each Redis key sequentially to avoid sentinel issues
            try:
                ticker_raw = await r.hgetall(ticker_key)
            except Exception as e:
                log.debug("ticker fetch error: %s", e)
                record_source_unavailable("redis", "ticker", type(e).__name__)
                ticker_raw = {}
            try:
                raw_1s = await r.zrevrange(candle_1s_key, 0, 0)
            except Exception as e:
                log.debug("1s fetch error: %s", e)
                raw_1s = []
            try:
                raw_1m = await r.zrevrange(candle_1m_key, 0, 0)
            except Exception as e:
                log.debug("1m fetch error: %s", e)
                raw_1m = []
            try:
                raw_1m_scores = await r.zrevrange(candle_1m_key, 0, 0, withscores=True)
            except Exception as e:
                log.debug("1m scores fetch error: %s", e)
                raw_1m_scores = []
            try:
                raw_trade = await r.zrevrange(trade_key, 0, 0)
            except Exception as e:
                log.debug("trade fetch error: %s", e)
                raw_trade = []
            record_source_lookup(
                source="redis",
                data_type="candle_multi_legacy",
                duration_sec=time.monotonic() - cycle_start,
                success=bool(ticker_raw),
            )

            live_price = float(ticker_raw["price"]) if ticker_raw.get("price") else None
            live_ts = int(ticker_raw["event_time"]) if ticker_raw.get("event_time") else None

            # Parse latest trade
            trade_price: float | None = None
            trade_ts: int = 0
            trade_qty: float = 0.0
            if raw_trade:
                try:
                    t = json.loads(raw_trade[0])
                    trade_price = float(t["p"])
                    trade_ts = int(t["t"])
                    trade_qty = float(t.get("q", 0))
                except Exception as e:
                    log.debug("trade parse error: %s", e)

            # Parse 1s candle
            candle_1s: dict | None = None
            if raw_1s:
                try:
                    c = json.loads(raw_1s[0])
                    candle_1s = {
                        "openTime": int(c["t"]),
                        "open": c["o"], "high": c["h"],
                        "low": c["l"], "close": c["c"],
                        "volume": c["v"],
                    }
                except Exception as e:
                    log.debug("1s parse error: %s", e)

            # Parse 1m candles
            candle_1m_window = 0
            candle_1m_data: list[dict] = []
            if raw_1m_scores:
                try:
                    latest_score = int(raw_1m_scores[0][1])
                    candle_1m_window = (latest_score // 60000) * 60000
                except Exception as e:
                    log.debug("1m window error: %s", e)
            if raw_1m:
                try:
                    candle_1m_data = [json.loads(c) for c in raw_1m]
                except Exception as e:
                    log.debug("1m parse error: %s", e)


            # Real-time update from trade
            trade_changed = (
                trade_price is not None
                and (trade_ts != last_trade_ts or trade_price != last_trade_price)
            )
            if trade_changed and trade_price is not None:
                rt_candles = _merge_trade_to_candles(
                    rt_candles, trade_ts, trade_price, trade_qty,
                    candle_1s, candle_1m_window, candle_1m_data,
                    target_ms_map,
                )


            # Build result for all intervals
            result: dict[str, dict | None] = {}
            for iv in ALL_INTERVALS:
                result[iv] = _get_stream_candle(
                    iv, rt_candles, candle_1s, candle_1m_window,
                    candle_1m_data, live_price, live_ts, target_ms_map,
                )
                # Accumulate trade qty into real-time candle
                if trade_qty > 0 and result[iv]:
                    result[iv]["volume"] = round(result[iv].get("volume", 0) + trade_qty, 8)

            result["T3"] = int(time.time() * 1000)
            push_start = time.monotonic()
            wire = json.dumps(result, default=str).encode("utf-8")
            try:
                await websocket.send_bytes(wire)
                record_ws_message_push(
                    route="/stream/all_legacy",
                    data_type="multi",
                    size_bytes=len(wire),
                    duration_sec=time.monotonic() - push_start,
                )
            except Exception:
                record_ws_message_push(
                    route="/stream/all_legacy",
                    data_type="multi",
                    size_bytes=len(wire),
                    duration_sec=time.monotonic() - push_start,
                    dropped=True,
                    drop_reason="send_failed",
                )
                raise
            last_trade_ts = trade_ts
            last_trade_price = trade_price or 0

            await asyncio.sleep(0.05)
            record_ws_loop_cycle(
                route="/stream/all_legacy",
                duration_sec=time.monotonic() - cycle_start,
            )
    except WebSocketDisconnect:
        record_ws_disconnect(
            route="/stream/all_legacy",
            reason="client_close",
            lifetime_sec=time.monotonic() - connect_time,
        )
    except Exception as e:
        record_ws_disconnect(
            route="/stream/all_legacy",
            reason="error",
            lifetime_sec=time.monotonic() - connect_time,
        )
        record_ws_connection_error(route="/stream/all_legacy", error_type=type(e).__name__)
        log.warning("Stream all error for %s: %s", symbol, e)


def _merge_trade_to_candles(
    rt_candles: dict[str, dict],
    trade_ts: int,
    trade_price: float,
    trade_qty: float,
    candle_1s: dict | None,
    candle_1m_window: int,
    candle_1m_data: list[dict],
    target_ms_map: dict[str, int],
) -> dict[str, dict]:
    """Merge a trade into real-time candle state for all intervals."""
    if not rt_candles:
        # Initialize from historical data
        for iv in ALL_INTERVALS:
            target_ms = target_ms_map[iv]
            if iv == "1s" and candle_1s:
                rt_candles[iv] = dict(candle_1s)
            elif candle_1m_data:
                window = (candle_1m_window // target_ms) * target_ms
                rt_candles[iv] = {
                    "openTime": window,
                    "open": candle_1m_data[0]["o"],
                    "high": max(c["h"] for c in candle_1m_data),
                    "low": min(c["l"] for c in candle_1m_data),
                    "close": candle_1m_data[-1]["c"],
                    "volume": round(sum(c["v"] for c in candle_1m_data), 8),
                }

    # Update each interval with trade price
    for iv, target_ms in target_ms_map.items():
        window = (trade_ts // target_ms) * target_ms
        existing = rt_candles.get(iv)

        if existing and existing["openTime"] == window:
            # Update in-progress candle
            existing["close"] = trade_price
            existing["high"] = max(existing["high"], trade_price)
            existing["low"] = min(existing["low"], trade_price)
            existing["volume"] = round(existing.get("volume", 0) + trade_qty, 8)
        else:
            # New candle for this interval
            if iv == "1s" and candle_1s:
                open_p = candle_1s["open"]
            elif candle_1m_data:
                open_p = candle_1m_data[0]["o"]
            else:
                open_p = trade_price

            rt_candles[iv] = {
                "openTime": window,
                "open": open_p,
                "high": trade_price,
                "low": trade_price,
                "close": trade_price,
                "volume": round(trade_qty, 8),
            }

    return rt_candles


def _get_stream_candle(
    interval: str,
    rt_candles: dict[str, dict],
    candle_1s: dict | None,
    candle_1m_window: int,
    candle_1m_data: list[dict],
    live_price: float | None,
    live_ts: int | None,
    target_ms_map: dict[str, int],
) -> dict | None:
    """Get the latest candle for an interval.

    OH = from Flink candle (always correct, never synthetic).
    Close = from ticker price (realtime, updates every msg).
    High/Low = tracked across iterations in ``_rt_candle_cache``.
    """
    target_ms = target_ms_map[interval]
    cache_key = f"{exchange}:{symbol}:{interval}"

    if interval in rt_candles:
        return rt_candles[interval]

    if interval == "1s":
        return candle_1s

    if not candle_1m_data or not live_price or not live_ts:
        return None

    minute_start = (live_ts // target_ms) * target_ms
    flink_minute = (candle_1m_window // target_ms) * target_ms

    # Does Flink have a candle for this current minute?
    flink_current = (flink_minute == minute_start)

    if flink_current:
        # Flink has the current minute → use its OH + live close + track HL
        open_p = candle_1m_data[0]["o"]
        flink_h = max(c["h"] for c in candle_1m_data)
        flink_l = min(c["l"] for c in candle_1m_data)
    else:
        # Flink hasn't written this minute yet → use OH from last closed candle
        open_p = candle_1m_data[-1]["c"]
        flink_h = open_p
        flink_l = open_p

    # Track high/low across iterations via cache
    cached = _rt_candle_cache.get(cache_key)
    if cached and cached.get("openTime") == minute_start:
        # Same minute still forming → update from cache
        high_p = max(cached["high"], live_price, flink_h)
        low_p = min(cached["low"], live_price, flink_l)
    else:
        # New minute or first iteration → init
        high_p = max(live_price, flink_h)
        low_p = min(live_price, flink_l)

    # Persist for next iteration
    _rt_candle_cache[cache_key] = {
        "openTime": minute_start,
        "high": high_p,
        "low": low_p,
    }

    return {
        "openTime": minute_start,
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "close": live_price,
        "volume": round(sum(c["v"] for c in candle_1m_data), 8) if candle_1m_data else 0,
    }


@router.websocket("/stream/{interval}")
async def stream_interval(
    websocket: WebSocket,
    interval: str,
):
    """Real-time candle streaming for a single timeframe."""
    interval = interval.strip().lower()
    if interval not in ALL_INTERVALS:
        await websocket.accept()
        await websocket.send_json({"error": f"Unsupported interval: {interval}"})
        await websocket.close()
        return

    await websocket.accept()
    r = await get_redis()
    symbol = websocket.query_params.get("symbol", "BTCUSDT").upper()
    exchange = websocket.query_params.get("exchange", "binance").strip().lower() or "binance"
    target_ms = INTERVAL_SECONDS[interval] * 1000
    last_sent = None
    connect_time = time.monotonic()
    last_push_time = time.monotonic()
    record_ws_connection(route="/stream/interval", accepted=True)

    try:
        while True:
            cycle_start = time.monotonic()
            fetch_start = time.monotonic()
            ticker = await r.hgetall(f"ticker:latest:{exchange}:{symbol}")
            live_price = float(ticker["price"]) if ticker.get("price") else None
            live_ts = int(ticker["event_time"]) if ticker.get("event_time") else None

            candle = await _build_candle(
                r, symbol, interval, target_ms, exchange, live_price, live_ts,
            )
            fetch_duration = time.monotonic() - fetch_start
            record_source_lookup(
                source="redis",
                data_type=f"candle_{interval}",
                duration_sec=fetch_duration,
                success=bool(candle),
            )
            if ticker.get("event_time"):
                try:
                    record_source_freshness(
                        source="redis",
                        exchange=exchange,
                        symbol=symbol,
                        ts=int(ticker["event_time"]) / 1000.0,
                    )
                except (ValueError, TypeError):
                    pass

            now_push = time.monotonic()
            if candle and candle != last_sent:
                candle["T3"] = int(time.time() * 1000)
                push_start = now_push
                payload = json.dumps(candle, default=str).encode("utf-8")
                try:
                    await websocket.send_bytes(payload)
                    last_push_time = now_push
                    record_ws_message_push(
                        route="/stream/interval",
                        data_type=interval,
                        size_bytes=len(payload),
                        duration_sec=now_push - push_start,
                    )
                except Exception:
                    record_ws_message_push(
                        route="/stream/interval",
                        data_type=interval,
                        size_bytes=len(payload),
                        duration_sec=now_push - push_start,
                        dropped=True,
                        drop_reason="send_failed",
                    )
                    raise
                last_sent = candle
            else:
                record_ws_noop(route="/stream/interval", data_type=interval)
                # BB-3: Send heartbeat ping every 10s to prevent browser timeout
                if (now_push - last_push_time) >= 10.0:
                    try:
                        await websocket.send_bytes(b'{"type":"ping"}')
                        last_push_time = now_push
                    except Exception:
                        pass

            await asyncio.sleep(0.05)
            record_ws_loop_cycle(
                route="/stream/interval",
                duration_sec=time.monotonic() - cycle_start,
            )
    except WebSocketDisconnect:
        record_ws_disconnect(
            route="/stream/interval",
            reason="client_close",
            lifetime_sec=time.monotonic() - connect_time,
        )
    except Exception as e:
        record_ws_disconnect(
            route="/stream/interval",
            reason="error",
            lifetime_sec=time.monotonic() - connect_time,
        )
        record_ws_connection_error(route="/stream/interval", error_type=type(e).__name__)
        log.warning("Stream %s error for %s: %s", interval, symbol, e)


@router.websocket("/stream/indicators/{interval}")
async def stream_indicators(
    websocket: WebSocket,
    interval: str,
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
    symbol = websocket.query_params.get("symbol", "BTCUSDT").upper()
    exchange = websocket.query_params.get("exchange", "binance").strip().lower() or "binance"
    last_sent = None
    connect_time = time.monotonic()
    last_push_time = time.monotonic()
    record_ws_connection(route="/stream/indicators", accepted=True)

    try:
        while True:
            cycle_start = time.monotonic()
            fetch_start = time.monotonic()
            payload = await _build_indicator_snapshot(r, symbol, exchange, interval)
            fetch_duration = time.monotonic() - fetch_start
            record_source_lookup(
                source="redis",
                data_type=f"indicator_{interval}",
                duration_sec=fetch_duration,
                success=bool(payload),
            )

            now_push = time.monotonic()
            if payload and payload != last_sent:
                payload["T3"] = int(time.time() * 1000)
                push_start = now_push
                wire = json.dumps(payload, default=str).encode("utf-8")
                try:
                    await websocket.send_bytes(wire)
                    last_push_time = now_push
                    record_ws_message_push(
                        route="/stream/indicators",
                        data_type=interval,
                        size_bytes=len(wire),
                        duration_sec=now_push - push_start,
                    )
                except Exception:
                    record_ws_message_push(
                        route="/stream/indicators",
                        data_type=interval,
                        size_bytes=len(wire),
                        duration_sec=now_push - push_start,
                        dropped=True,
                        drop_reason="send_failed",
                    )
                    raise
                last_sent = payload
            else:
                record_ws_noop(route="/stream/indicators", data_type=interval)
                # BB-3: Send heartbeat ping every 10s to prevent browser timeout
                if (now_push - last_push_time) >= 10.0:
                    try:
                        await websocket.send_bytes(b'{"type":"ping"}')
                        last_push_time = now_push
                    except Exception:
                        pass

            await asyncio.sleep(0.05)
            record_ws_loop_cycle(
                route="/stream/indicators",
                duration_sec=time.monotonic() - cycle_start,
            )
    except WebSocketDisconnect:
        record_ws_disconnect(
            route="/stream/indicators",
            reason="client_close",
            lifetime_sec=time.monotonic() - connect_time,
        )
    except Exception as e:
        record_ws_disconnect(
            route="/stream/indicators",
            reason="error",
            lifetime_sec=time.monotonic() - connect_time,
        )
        record_ws_connection_error(route="/stream/indicators", error_type=type(e).__name__)
        log.warning("Indicator stream %s error for %s: %s", interval, symbol, e)


async def _stream_all_impl(websocket: WebSocket, symbol: str = "", exchange: str = "binance"):
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
    record_ws_connection(route="/stream/all", accepted=True)

    # Build target_ms lookup
    target_ms_map = {iv: INTERVAL_SECONDS[iv] * 1000 for iv in ALL_INTERVALS}
    last_sent: dict[str, dict | None] = {iv: None for iv in ALL_INTERVALS}
    last_ticker_ts: int = 0  # last ticker's event_time we pushed (epoch ms)
    connect_time = time.monotonic()
    last_push_time = time.monotonic()

    try:
        while True:
            result: dict[str, dict | None] = {}
            cycle_start = time.monotonic()
            any_changed = False

            # Fetch all data in one pipeline to avoid N+1 Redis calls
            candle_1s_key = f"candle:1s:{exchange}:{symbol}"
            candle_1m_key = f"candle:1m:{exchange}:{symbol}"
            trade_key = f"trade:latest:{exchange}:{symbol}"
            candle_latest_key = f"candle:latest:{exchange}:{symbol}"

            pipe = r.pipeline()
            pipe.hgetall(f"ticker:latest:{exchange}:{symbol}")
            pipe.zrevrange(candle_1s_key, 0, 0)
            pipe.zrevrange(candle_1m_key, 0, 0)
            pipe.zrevrange(candle_1m_key, 0, 0, withscores=True)
            pipe.zrevrange(trade_key, 0, 0)
            pipe.hgetall(candle_latest_key)
            pipeline_results = await pipe.execute()
            pipe_duration = time.monotonic() - cycle_start

            # Record the multi-source lookup (Redis pipeline success / failure)
            record_source_lookup(
                source="redis",
                data_type="candle_multi",
                duration_sec=pipe_duration,
                success=bool(pipeline_results and pipeline_results[0]),
            )
            record_source_chain_outcome(
                data_type="candle_multi",
                terminating_source="redis",
            )

            ticker = pipeline_results[0]
            raw_1s = pipeline_results[1]
            raw_1m = pipeline_results[2]
            raw_1m_scores = pipeline_results[3]
            raw_trade = pipeline_results[4]
            candle_latest = pipeline_results[5]

            # Record per-symbol source freshness
            if ticker.get("event_time"):
                try:
                    record_source_freshness(
                        source="redis",
                        exchange=exchange,
                        symbol=symbol,
                        ts=int(ticker["event_time"]) / 1000.0,
                    )
                except (ValueError, TypeError):
                    pass

            live_price = float(ticker["price"]) if ticker.get("price") else None
            live_ts = int(ticker["event_time"]) if ticker.get("event_time") else None

            # B9 fix removed: Flink now writes current event_time to Redis via
            # @ticker WS. OH from Flink candle + close from ticker = realtime.

            # Parse trade qty for volume accumulation
            trade_qty: float = 0.0
            if raw_trade:
                try:
                    t = json.loads(raw_trade[0])
                    trade_qty = float(t.get("q", 0))
                except Exception:
                    pass

            # Parse 1s candle
            candle_1s: dict | None = None
            if raw_1s:
                try:
                    c = json.loads(raw_1s[0])
                    candle_1s = {
                        "openTime": int(c["t"]),
                        "open": c["o"], "high": c["h"],
                        "low": c["l"], "close": c["c"],
                        "volume": c["v"],
                    }
                except Exception:
                    pass

            # Parse 1m candles
            candle_1m_window = 0
            candle_1m_data: list[dict] = []
            if raw_1m_scores:
                try:
                    latest_score = int(raw_1m_scores[0][1])
                    candle_1m_window = (latest_score // 60000) * 60000
                except Exception:
                    pass
            if raw_1m:
                try:
                    candle_1m_data = [json.loads(c) for c in raw_1m]
                except Exception:
                    pass

            # Build candles for all intervals using pre-fetched data
            for iv in ALL_INTERVALS:
                candle = _build_candle_from_data(
                    exchange, symbol, iv, candle_1s, candle_1m_window, candle_1m_data,
                    live_price, live_ts, target_ms_map[iv],
                    candle_latest,
                )
                # Accumulate trade qty into real-time candle
                if trade_qty > 0 and candle:
                    candle["volume"] = round(candle.get("volume", 0) + trade_qty, 8)
                if candle and candle != last_sent[iv]:
                    result[iv] = candle
                    last_sent[iv] = candle
                    any_changed = True
                else:
                    result[iv] = last_sent[iv]
                    if candle is None:
                        record_ws_noop(route="/stream/all", data_type=iv)

            # Add ticker metadata for frontend (full Binance @ticker fields)
            if ticker and live_price and live_ts:
                result["_ticker"] = {
                    "price": live_price,
                    "event_time": live_ts,
                    "bid": float(ticker.get("bid", 0) or 0),
                    "ask": float(ticker.get("ask", 0) or 0),
                    "bid_qty": float(ticker.get("bid_qty", 0) or 0),
                    "ask_qty": float(ticker.get("ask_qty", 0) or 0),
                    "volume": float(ticker.get("volume", 0) or 0),
                    "quote_volume": float(ticker.get("quote_volume", 0) or 0),
                    "change24h": float(ticker.get("change24h", 0) or 0),
                    "change_pct": float(ticker.get("change_pct", 0) or 0),
                    "change_abs": float(ticker.get("change_abs", 0) or 0),
                    "weighted_avg": float(ticker.get("weighted_avg", 0) or 0),
                    "open_24h": float(ticker.get("open_24h", 0) or 0),
                    "high_24h": float(ticker.get("high_24h", 0) or 0),
                    "low_24h": float(ticker.get("low_24h", 0) or 0),
                    "last_qty": float(ticker.get("last_qty", 0) or 0),
                }

            # Only send if something changed OR a newer ticker tick arrived.
            # The ticker can tick faster than any interval's candle bucket
            # rolls (e.g. 1s ticker, 1m candle) so without this the forming
            # candle's price appears frozen between candle buckets.
            now_push = time.monotonic()
            ticker_updated = bool(live_ts and live_ts > last_ticker_ts)
            if any_changed or ticker_updated:
                if ticker_updated:
                    last_ticker_ts = live_ts
                result["T3"] = int(time.time() * 1000)
                push_start = now_push
                payload = json.dumps(result, default=str).encode("utf-8")
                try:
                    await websocket.send_bytes(payload)
                    last_push_time = now_push
                    record_ws_message_push(
                        route="/stream/all",
                        data_type="multi",
                        size_bytes=len(payload),
                        duration_sec=now_push - push_start,
                    )
                except Exception as push_exc:
                    record_ws_message_push(
                        route="/stream/all",
                        data_type="multi",
                        size_bytes=len(payload),
                        duration_sec=now_push - push_start,
                        dropped=True,
                        drop_reason=type(push_exc).__name__,
                    )
                    raise
            elif (now_push - last_push_time) >= 10.0:
                # BB-3: Send heartbeat ping every 10s to prevent browser timeout
                try:
                    await websocket.send_bytes(b'{"type":"ping"}')
                    last_push_time = now_push
                except Exception:
                    pass

            # CRITICAL: Reduced from 0.3s to 0.05s for real-time responsiveness
            # This is the primary latency source — tighter loop = faster updates
            await asyncio.sleep(0.05)
            record_ws_loop_cycle(
                route="/stream/all",
                duration_sec=time.monotonic() - cycle_start,
            )
    except WebSocketDisconnect:
        lifetime = time.monotonic() - connect_time
        record_ws_disconnect(route="/stream/all", reason="client_close", lifetime_sec=lifetime)
    except Exception as e:
        lifetime = time.monotonic() - connect_time
        log.warning("Stream all error for %s: %s", symbol, e)
        record_ws_disconnect(route="/stream/all", reason="error", lifetime_sec=lifetime)
        record_ws_connection_error(route="/stream/all", error_type=type(e).__name__)


def _build_candle_from_data(
    exchange: str,
    symbol: str,
    interval: str,
    candle_1s: dict | None,
    candle_1m_window: int,
    candle_1m_data: list[dict],
    live_price: float | None,
    live_ts: int | None,
    target_ms: int,
    candle_latest: dict,
) -> dict | None:
    """Build candle from pre-fetched Redis data.

    Phase 1: OH from Flink (always correct), close from ticker (realtime),
    high/low tracked across iterations via _rt_candle_cache.
    """
    cache_key = f"{exchange}:{symbol}:{interval}"

    if interval == "1s":
        if candle_1s:
            return {
                "openTime": candle_1s["openTime"],
                "open": candle_1s["open"],
                "high": candle_1s["high"],
                "low": candle_1s["low"],
                "close": candle_1s["close"],
                "volume": candle_1s["volume"],
            }
        return None

    if not live_price or not live_ts:
        return None

    minute_start = (live_ts // target_ms) * target_ms
    flink_candle = None
    flink_window = 0

    if candle_1m_data:
        latest_score = candle_1m_window if candle_1m_window else 0
        flink_window = (latest_score // target_ms) * target_ms
        flink_candle = {
            "openTime": flink_window,
            "open": candle_1m_data[0]["o"],
            "high": max(c["h"] for c in candle_1m_data),
            "low": min(c["l"] for c in candle_1m_data),
            "close": candle_1m_data[-1]["c"],
            "volume": round(sum(c["v"] for c in candle_1m_data), 8),
        }

    # ── Determine OH for current forming candle ─────────────────────────
    if flink_candle and flink_window == minute_start:
        # Flink has data for this minute → use its OH
        open_p = flink_candle["open"]
        flink_h = flink_candle["high"]
        flink_l = flink_candle["low"]
    elif flink_candle:
        # Flink hasn't written this minute yet → OH from last closed candle
        open_p = flink_candle["close"]
        flink_h = open_p
        flink_l = open_p
    else:
        # No Flink data at all → start from live price
        open_p = live_price
        flink_h = live_price
        flink_l = live_price

    # ── Track high/low across iterations ───────────────────────────────
    cached = _rt_candle_cache.get(cache_key)
    if cached and cached.get("openTime") == minute_start:
        high_p = max(cached["high"], live_price, flink_h)
        low_p = min(cached["low"], live_price, flink_l)
    else:
        high_p = max(live_price, flink_h)
        low_p = min(live_price, flink_l)

    # ── Persist for next iteration ──────────────────────────────────────
    _rt_candle_cache[cache_key] = {
        "openTime": minute_start,
        "high": high_p,
        "low": low_p,
    }

    return {
        "openTime": minute_start,
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "close": live_price,
        "volume": flink_candle["volume"] if flink_candle else 0,
    }


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
    real-time ticker price."""

    if live_price is None or live_ts is None:
        ticker = await r.hgetall(f"ticker:latest:{exchange}:{symbol}")
        live_price = live_price or (float(ticker["price"]) if ticker.get("price") else None)
        live_ts = live_ts or (int(ticker["event_time"]) if ticker.get("event_time") else None)

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
        if live_price and live_ts:
            live_window = (live_ts // target_ms) * target_ms
            return {
                "openTime": live_window,
                "open": live_price,
                "high": live_price,
                "low": live_price,
                "close": live_price,
                "volume": 0,
            }
        return None

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

    # Keep 1m responsive even when kline streams lag by folding in fresh ticker.
    if interval == "1m":
        if live_price and live_ts:
            live_window = (live_ts // target_ms) * target_ms
            if flink_candle and live_window == flink_window:
                if live_ts > latest_source_ts:
                    flink_candle["close"] = live_price
                    flink_candle["high"] = max(flink_candle["high"], live_price)
                    flink_candle["low"] = min(flink_candle["low"], live_price)
                return flink_candle
            if live_window > flink_window:
                return {
                    "openTime": live_window,
                    "open": live_price,
                    "high": live_price,
                    "low": live_price,
                    "close": live_price,
                    "volume": 0,
                }
        return flink_candle

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
