"""Entrypoint for binance-kline-ws Swarm service.

Spawns ``KLINE_WS_SHARDS`` parallel WebSocket connections to Binance,
subscribes to ``{symbol}@kline_1s`` for each symbol, parses kline
payloads, and writes to Redis sorted set ``candle:1s:binance:{symbol}``
via a batched pipeline.

This is the low-latency path for 1s klines — bypasses Kafka/Flink entirely.
Latency target: <200ms from Binance emit → Redis write.

Also exposes Prometheus metrics on ``:9102/metrics`` and HTTP health on
``:9102/healthz``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from typing import List

import aiohttp
import redis.asyncio as redis_async
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from aiohttp import web

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.kline_ws.config import KlineWsConfig  # noqa: E402
from src.kline_ws.redis_writer import KlineWsRedisWriter  # noqa: E402
from src.kline_ws.shard import KlineWsShard  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
log = logging.getLogger("binance-kline-ws")

# ── Prometheus metrics ────────────────────────────────────────────────────

FRAMES_TOTAL = Counter(
    "kline_ws_frames_total", "Total WS frames received across all shards"
)
CANDLES_TOTAL = Counter(
    "kline_ws_candles_total", "Total 1s candles parsed and buffered"
)
RECONNECTS_TOTAL = Counter(
    "kline_ws_reconnects_total", "Total reconnect attempts"
)
SHARDS_UP = Gauge(
    "kline_ws_shards_up", "Number of shards currently connected"
)
REDIS_BUFFER_SIZE = Gauge(
    "kline_ws_redis_buffer_size", "Pending items in Redis writer buffer"
)
REDIS_WRITE_LATENCY = Histogram(
    "kline_ws_redis_flush_seconds",
    "Redis pipeline flush latency",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
EVENT_TO_WRITE_LATENCY = Histogram(
    "kline_ws_event_to_now_seconds",
    "Binance event_time → now() in our process",
    buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0),
)

# ── Redis connection (Sentinel-aware, fallback to direct) ───────────────

REDIS_SENTINELS = os.environ.get(
    "REDIS_SENTINELS", "redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379"
)
REDIS_MASTER_NAME = os.environ.get("REDIS_MASTER_NAME", "mymaster")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-master")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

async def get_redis() -> redis_async.Redis:
    """Build Redis async client (master-only for writes)."""
    sentinel_nodes = [
        tuple(node.split(":")) for node in REDIS_SENTINELS.split(",")
        if node.strip()
    ]
    try:
        from redis.asyncio.sentinel import Sentinel as AsyncSentinel
        sentinel = AsyncSentinel(
            sentinel_nodes, socket_timeout=0.5, socket_connect_timeout=0.5,
        )
        client = sentinel.master_for(
            REDIS_MASTER_NAME,
            socket_timeout=1.0, socket_connect_timeout=1.0,
            decode_responses=False, max_connections=64,
        )
        await client.ping()
        log.info("Redis connected via Sentinel (%s)", REDIS_MASTER_NAME)
        return client
    except Exception as e:
        log.warning("Sentinel connect failed (%s), fallback to direct %s:%d",
                    e, REDIS_HOST, REDIS_PORT)
        client = redis_async.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=False, socket_keepalive=True,
            health_check_interval=30, max_connections=64,
        )
        await client.ping()
        log.info("Redis connected via direct %s:%d", REDIS_HOST, REDIS_PORT)
        return client

# ── Health / metrics HTTP server ──────────────────────────────────────────

HTTP_HOST = os.environ.get("METRICS_HOST", "0.0.0.0")
HTTP_PORT = int(os.environ.get("METRICS_PORT", "9102"))

async def metrics_handler(request: web.Request) -> web.Response:
    body = generate_latest()
    return web.Response(body=body, content_type=CONTENT_TYPE_LATEST)

async def healthz_handler(request: web.Request) -> web.Response:
    body = {
        "ok": True,
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "shards": SHARD_STATS,
    }
    return web.json_response(body)

SHARD_STATS: list = []
STARTED_AT = time.time()

async def start_http() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/healthz", healthz_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
    await site.start()
    log.info("HTTP server on http://%s:%d (metrics, healthz)", HTTP_HOST, HTTP_PORT)
    return runner

# ── Stats reporter ──────────────────────────────────────────────────────

async def stats_reporter(
    shards: List[KlineWsShard], writer: KlineWsRedisWriter
) -> None:
    """Update Prometheus gauges + log stats every 5s."""
    while True:
        await asyncio.sleep(5)
        up = sum(1 for s in shards if s.connected)
        SHARDS_UP.set(up)
        REDIS_BUFFER_SIZE.set(len(writer._buffer))
        SHARD_STATS.clear()
        for s in shards:
            SHARD_STATS.append(s.stats)
        log.debug(
            "shards_up=%d buffer=%d candles_total=%d",
            up, len(writer._buffer), sum(s.candles_total for s in shards),
        )

# ── Main ─────────────────────────────────────────────────────────────────

async def main() -> None:
    global SHARD_STATS

    # 1. Load symbol list
    config = await KlineWsConfig.load()
    log.info(
        "Config: %d shards, total %d symbols",
        len(config.shards), config.total_symbols,
    )

    # 2. Start HTTP server
    await start_http()

    # 3. Build Redis writer
    redis = await get_redis()
    log.info("Redis OK")
    writer = KlineWsRedisWriter(redis)
    await writer.start()

    # 4. Build shards
    shards: List[KlineWsShard] = []
    for i in range(len(config.shards)):
        if not config.shards[i]:
            log.warning("[kline-shard %d] no symbols, skipping", i)
            continue
        url = config.shard_url(i)
        shards.append(KlineWsShard(i, url, writer))

    # 5. Start shard tasks
    stop_event = asyncio.Event()
    shard_tasks = [
        asyncio.create_task(s.run(stop_event), name=f"kline-shard-{i}")
        for i, s in enumerate(shards)
    ]
    stats_task = asyncio.create_task(
        stats_reporter(shards, writer), name="kline-stats"
    )

    # 6. Wait for shutdown signal
    loop = asyncio.get_running_loop()

    def _signal_handler() -> None:
        log.info("shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    finally:
        log.info("stopping %d shards...", len(shards))
        stop_event.set()
        await asyncio.gather(*shard_tasks, return_exceptions=True)
        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass
        await writer.stop()
        await redis.close()
        log.info("bye")


if __name__ == "__main__":
    asyncio.run(main())
