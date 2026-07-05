#!/usr/bin/env python3
"""
Combined-stream Kafka producer.

Subscribes to Binance combined-stream endpoint
(``wss://stream.binance.com:9443/stream?streams=…``) for all
USDT-perpetual symbols and publishes the 4 required data streams
to the same Kafka topics the legacy producer wrote to:

- ``!ticker@arr`` (batch 24hr ticker for all symbols) → ``crypto_ticker``
- ``{symbol}@kline_1s``                     → ``crypto_klines``
- ``{symbol}@depth20@100ms``                 → ``crypto_depth``
- ``{symbol}@aggTrade``                      → ``crypto_trades``

Design goals:
- Single WS connection (avoids 403-per-connection block).
- Async I/O (<1 % CPU, minimal memory).
- Reuse production ``mappers``, ``avro_serializer``, ``kafka_client``
  so downstream consumers (Flink, Spark, KeyDB writer) see exactly
  the same record format.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Optional

import aiohttp
import websockets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.avro_serializer import AvroSerializer
from common.config import MAX_SYMBOLS
from common.kafka_client import flush_and_close, init_producer, send_to_kafka
from common.logging import setup_logging_from_env
from exchanges.binance.mappers import (
    map_agg_trade,
    map_depth,
    map_kline,
    map_ticker,
    map_ticker_rest,
)

log = logging.getLogger("combined_stream")

# ── Constants ────────────────────────────────────────────────────────────────

BINANCE_WS = "wss://stream.binance.com:9443/stream"
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/ticker/24hr"
SCHEMA_REGISTRY_URL = os.environ.get("SCHEMA_REGISTRY_URL", "http://schema-registry:8080/apis/ccompat/v7")

RECONNECT_BASE = 2.0
RECONNECT_MAX = 120.0
PING_INTERVAL = 30.0
WS_TIMEOUT = 60.0

KAFKA_TOPIC_TICKER = os.environ.get("KAFKA_TOPIC_TICKER", "crypto_ticker")
KAFKA_TOPIC_KLINES = os.environ.get("KAFKA_TOPIC_KLINES", "crypto_klines")
KAFKA_TOPIC_DEPTH = os.environ.get("KAFKA_TOPIC_DEPTH", "crypto_depth")
KAFKA_TOPIC_TRADES = os.environ.get("KAFKA_TOPIC_TRADES", "crypto_trades")

# ── Global Kafka producer handle (lazy init) ────────────────────────────────
_avro: AvroSerializer | None = None
_sent_counter: int = 0
_msg_counter: int = 0
_loop: asyncio.AbstractEventLoop | None = None


async def periodic_status():
    """Log message rate every 30s."""
    while True:
        await asyncio.sleep(30)
        log.info("[STATUS] msgs=%d sent=%d", _msg_counter, _sent_counter)


def init_kafka():
    global _avro
    if _avro is None:
        _avro = AvroSerializer(SCHEMA_REGISTRY_URL)
        # Register Avro schemas for all topics
        schema_map = {
            "crypto_ticker": "schemas/ticker.avsc",
            "crypto_klines": "schemas/kline.avsc",
            "crypto_depth": "schemas/depth.avsc",
            "crypto_trades": "schemas/trade.avsc",
        }
        for topic, path in schema_map.items():
            _avro.register(topic, path)
        init_producer()
        log.info("Kafka producer + Avro ready")


async def send(topic: str, record: dict):
    """Publish a single record to Kafka via the executor (non-blocking)."""
    global _sent_counter
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, send_to_kafka, topic, record, _avro)
        _sent_counter += 1
    except Exception as e:
        log.error("[%s] send error: %s", topic, e)


# ── Fetch top USDT symbols ───────────────────────────────────────────────

async def fetch_symbols(max_symbols: int = 200) -> list[str]:
    """Fetch top USDT symbols from Binance REST, sorted by 24h quote volume."""
    log.info("Fetching top %d symbols from %s", max_symbols, EXCHANGE_INFO_URL)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(EXCHANGE_INFO_URL) as resp:
            resp.raise_for_status()
            rows = await resp.json()
    usdt_rows = [
        r for r in rows
        if r.get("symbol", "").endswith("USDT")
        and r.get("quoteVolume") not in (None, "", "0", "0.0")
    ]
    usdt_rows.sort(key=lambda r: float(r.get("quoteVolume") or 0), reverse=True)
    symbols = [r["symbol"] for r in usdt_rows[:max_symbols]]
    log.info("Loaded %d USDT symbols", len(symbols))
    return symbols


# ── Build combined stream URL ────────────────────────────────────────────────

def build_streams(symbols: list[str]) -> list[str]:
    """Build a list of stream names for the combined WS URL."""
    streams: list[str] = []
    # Batch ticker (single stream, all symbols)
    streams.append("!ticker@arr")
    # Per‑symbol streams
    for sym in symbols:
        sl = sym.lower()
        streams.append(f"{sl}@kline_1s")
        streams.append(f"{sl}@depth20@100ms")
        streams.append(f"{sl}@aggTrade")
    log.info("Total streams: %d", len(streams))
    return streams


def build_url(streams: list[str]) -> str:
    return f"{BINANCE_WS}?streams={'/'.join(streams)}"


# ── Message handlers ─────────────────────────────────────────────────────────

async def handle_ticker_arr(items: list[dict]):
    """Process !ticker@arr batch (all symbols at once)."""
    for raw in items:
        symbol = raw.get("s", "")
        if not symbol.endswith("USDT"):
            continue
        await send(KAFKA_TOPIC_TICKER, map_ticker(raw))


async def handle_kline(data: dict):
    """Process {symbol}@kline_1s."""
    if (data.get("s") or "").endswith("USDT"):
        await send(KAFKA_TOPIC_KLINES, map_kline(data))


async def handle_trade(data: dict):
    """Process {symbol}@aggTrade."""
    if (data.get("s") or "").endswith("USDT"):
        await send(KAFKA_TOPIC_TRADES, map_agg_trade(data))


async def handle_depth(data: dict):
    """Process {symbol}@depth20@100ms depth snapshot."""
    # Symbol may come from stream-derived _symbol (depth snapshot lacks "s" field)
    symbol = data.pop("_symbol", None) or data.get("s") or ""
    if symbol.endswith("USDT"):
        # Inject symbol into data so map_depth picks it up
        data["s"] = symbol
        await send(KAFKA_TOPIC_DEPTH, map_depth(data))


DISPATCH = {
    "!ticker@arr": lambda d, _stream: handle_ticker_arr(d) if isinstance(d, list) else None,
}


def route(stream: str, data: Any) -> Optional[asyncio.Task]:
    """Route a combined-stream message to the matching handler.

    Returns an awaitable or None if unknown stream type.
    """
    if stream == "!ticker@arr" and isinstance(data, list):
        return asyncio.ensure_future(handle_ticker_arr(data))

    # Extract the stream type from the second part: "btcusdt@kline_1s" -> "kline_1s"
    parts = stream.split("@", 1)
    if len(parts) < 2:
        return None
    stype = parts[1]

    if stype == "kline_1s" and isinstance(data, dict):
        return asyncio.ensure_future(handle_kline(data))
    if stype.startswith("depth"):
        if not isinstance(data, dict):
            log.warning("[ROUTE] depth data not dict: type=%s", type(data).__name__)
            return None
        # Depth snapshot from depth20@100ms may not have "s" key; derive from stream name
        symbol = parts[0].upper()  # e.g. "BTCUSDT"
        if not symbol.endswith("USDT"):
            return None
        data["_symbol"] = symbol  # inject derived symbol
        return asyncio.ensure_future(handle_depth(data))
    if stype == "aggTrade" and isinstance(data, dict):
        return asyncio.ensure_future(handle_trade(data))
    return None


# ── WebSocket loop ───────────────────────────────────────────────────────────

async def ws_loop(symbols: list[str]):
    """Connect to the combined WS and stream indefinitely."""
    streams = build_streams(symbols)
    url = build_url(streams)
    log.info("Connecting to combined WS (%d streams)", len(streams))

    global _msg_counter
    delay = RECONNECT_BASE
    while True:
        try:
            async with websockets.connect(
                url,
                ping_interval=PING_INTERVAL,
                ping_timeout=10,
                close_timeout=5,
                max_size=2**21,  # 2 MB max message
                open_timeout=30,            ) as ws:
                log.info("WebSocket connected")
                delay = RECONNECT_BASE
                async for msg in ws:
                    _msg_counter += 1
                    parsed = json.loads(msg)
                    stream_name = parsed.get("stream", "")
                    data = parsed.get("data")
                    if stream_name and data is not None:
                        task = route(stream_name, data)
                        if task is None:
                            log.debug("[WS] Unhandled stream: %s", stream_name)
                    else:
                        log.debug("[WS] Skipping msg stream=%r data=%r", stream_name, data is not None)

        except asyncio.TimeoutError:
            log.warning("WS read timeout, reconnecting...")
        except Exception as e:
            log.error("WS error: %s (reconnect in %.1fs)", e, delay)
        await asyncio.sleep(delay)
        delay = min(delay * 2, RECONNECT_MAX)


# ── Health HTTP server ───────────────────────────────────────────────────────

async def health_server():
    """Simple HTTP health endpoint on port 8000 (used by Docker healthcheck)."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "0.0.0.0", 8000)
    log.info("Health server on 0.0.0.0:8000")
    async with server:
        await server.serve_forever()

# ── REST ticker poller ───────────────────────────────────────────────────────
# Binance !ticker@arr WebSocket stream is geo-blocked from AWS (returns 403)
# just like aggTrade and depth. The combined stream works for klines but not
# ticker. This REST poller provides 24hr ticker data via Binance REST API
# which is NOT blocked, published to the same crypto_ticker Kafka topic.
# Polls every 60 seconds (same frequency as !ticker@arr updates).

REST_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"

async def rest_ticker_poller():
    """Poll REST 24hr ticker and publish to crypto_ticker Kafka topic."""
    import aiohttp
    log.info("[REST-Ticker] Starting REST 24hr ticker poller (60s interval)")
    delay = 60.0
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(REST_TICKER_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        log.warning("[REST-Ticker] HTTP %d, retrying in %.0fs", resp.status, delay)
                        await asyncio.sleep(delay)
                        continue
                    items = await resp.json()
        except Exception as e:
            log.warning("[REST-Ticker] Fetch error: %s, retrying in %.0fs", e, delay)
            await asyncio.sleep(delay)
            continue

        count = 0
        for raw in items:
            # REST API uses 'symbol' field, not 's' (WebSocket convention)
            symbol = raw.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue
            try:
                await send(KAFKA_TOPIC_TICKER, map_ticker_rest(raw))
                count += 1
            except Exception as e:
                log.error("[REST-Ticker] send error for %s: %s", symbol, e)
        log.info("[REST-Ticker] Published %d tickers to %s", count, KAFKA_TOPIC_TICKER)
        await asyncio.sleep(delay)


# ── Main ─────────────────────────────────────────────────────────────────────

async def amain():
    setup_logging_from_env()
    log.info("Starting combined-stream producer")
    init_kafka()
    symbols = await fetch_symbols(MAX_SYMBOLS)
    log.info("Monitoring %d USDT symbols", len(symbols))

    await asyncio.gather(
        health_server(),
        ws_loop(symbols),
        rest_ticker_poller(),
        periodic_status(),
        return_exceptions=True,
    )


def run():
    """Entry point for Docker CMD."""
    asyncio.run(amain())


if __name__ == "__main__":
    run()
