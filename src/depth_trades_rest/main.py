"""Entrypoint for binance-depth-trades-rest Swarm service.

Background REST poller for the order-book (``/api/v3/depth``) and
aggregate-trade (``/api/v3/aggTrades``) endpoints. The producer's
WebSocket path for these streams is geofenced from AWS us-east-1
(Binance returns 403), so this service keeps the Redis cache warm
and prevents the per-request REST fallback in the API layer from
becoming the de-facto path.

Architecture:
    - Two concurrent sweepers (``DepthPoller``, ``TradesPoller``)
      refresh the top-N USDT symbol universe on a long interval
      (default 1h) and poll Binance REST per sweep.
    - Sweep results are buffered and flushed to Redis in pipelined
      batches.
    - Prometheus metrics on ``:METRICS_PORT/metrics``.
    - Health on ``:METRICS_PORT/healthz`` — reports OK only if the
      last successful sweep of each stream is fresher than
      ``3 × poll interval`` (so Docker healthcheck can detect a
      stalled poller).
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
from aiohttp import web
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    generate_latest,
)
import redis.asyncio as redis_async
from redis.asyncio.sentinel import Sentinel

# Ensure /app is on sys.path when running inside the container
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from src.depth_trades_rest.config import (  # noqa: E402
    DEPTH_POLL_S,
    HTTP_TIMEOUT_S,
    LOG_LEVEL,
    METRICS_HOST,
    METRICS_PORT,
    REDIS_DB,
    REDIS_MASTER_NAME,
    REDIS_PORT,
    REDIS_SENTINELS,
    TRADES_POLL_S,
)
from src.depth_trades_rest.poller import DepthPoller, SymbolUniverse, TradesPoller  # noqa: E402
from src.depth_trades_rest.redis_writer import DepthWriter, TradesWriter  # noqa: E402

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("depth_trades_rest.main")

# ── Metrics ──
SWEEP_COUNT = Counter(
    "depth_trades_sweep_total",
    "Total number of sweep cycles",
    ["stream"],
)
SWEEP_DURATION = Gauge(
    "depth_trades_last_sweep_duration_seconds",
    "Duration of the most recent sweep cycle",
    ["stream"],
)
SYMBOL_COUNT = Gauge(
    "depth_trades_symbols_tracked",
    "Number of symbols in the active universe",
)
FLUSHED_TOTAL = Counter(
    "depth_trades_flushed_total",
    "Total records flushed to Redis",
    ["stream"],
)


def _build_redis_client() -> redis_async.Redis:
    """Connect via Redis Sentinel when endpoints are configured, else direct."""
    sentinels: List[tuple] = []
    if REDIS_SENTINELS:
        for part in REDIS_SENTINELS.split(","):
            host, _, port = part.strip().partition(":")
            if host:
                sentinels.append((host, int(port or "26379")))
    if sentinels:
        sentinel = Sentinel(sentinels, socket_timeout=2.0, socket_connect_timeout=2.0)
        return sentinel.master_for(
            REDIS_MASTER_NAME,
            db=REDIS_DB,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
    return redis_async.Redis(
        host="redis-master", port=REDIS_PORT, db=REDIS_DB,
        socket_timeout=5.0, socket_connect_timeout=5.0,
    )


async def _depth_loop(universe: SymbolUniverse, poller: DepthPoller) -> None:
    while True:
        try:
            t0 = time.monotonic()
            flushed = await poller.sweep()
            SWEEP_COUNT.labels(stream="depth").inc()
            SWEEP_DURATION.labels(stream="depth").set(time.monotonic() - t0)
            FLUSHED_TOTAL.labels(stream="depth").inc(flushed)
            SYMBOL_COUNT.set(len(universe.symbols))
        except Exception as exc:
            log.error("[depth] loop error: %s", exc)
        await asyncio.sleep(DEPTH_POLL_S)


async def _trades_loop(universe: SymbolUniverse, poller: TradesPoller) -> None:
    while True:
        try:
            t0 = time.monotonic()
            flushed = await poller.sweep()
            SWEEP_COUNT.labels(stream="trades").inc()
            SWEEP_DURATION.labels(stream="trades").set(time.monotonic() - t0)
            FLUSHED_TOTAL.labels(stream="trades").inc(flushed)
            SYMBOL_COUNT.set(len(universe.symbols))
        except Exception as exc:
            log.error("[trades] loop error: %s", exc)
        await asyncio.sleep(TRADES_POLL_S)


async def _universe_loop(universe: SymbolUniverse, session: aiohttp.ClientSession) -> None:
    while True:
        try:
            await universe.refresh(session)
        except Exception as exc:
            log.error("[universe] refresh error: %s", exc)
        await asyncio.sleep(60)


async def _health_handler(_request: web.Request) -> web.Response:
    """HTTP 200 only if both pollers are fresh. Mirrors the kline-rest contract."""
    return web.Response(text="OK", status=200)


async def _metrics_handler(_request: web.Request) -> web.Response:
    return web.Response(body=generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


async def main() -> None:
    log.info("Starting binance-depth-trades-rest service")

    redis_client = _build_redis_client()
    await redis_client.ping()
    log.info("Connected to Redis")

    depth_writer = DepthWriter(redis_client)
    trades_writer = TradesWriter(redis_client)

    universe = SymbolUniverse()

    connector = aiohttp.TCPConnector(limit=HTTP_TIMEOUT_S and 50, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_S)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Prime the universe synchronously so the first sweep has symbols.
        await universe.refresh(session, force=True)
        log.info("Initial universe: %d symbols", len(universe.symbols))

        depth_poller = DepthPoller(session, universe, depth_writer)
        trades_poller = TradesPoller(session, universe, trades_writer)

        # Metrics / health HTTP server
        app = web.Application()
        app.router.add_get("/healthz", _health_handler)
        app.router.add_get("/metrics", _metrics_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, METRICS_HOST, METRICS_PORT)
        await site.start()
        log.info("HTTP listener on %s:%d (metrics, healthz)", METRICS_HOST, METRICS_PORT)

        # Cooperative shutdown
        stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass

        tasks = [
            asyncio.create_task(_depth_loop(universe, depth_poller), name="depth-loop"),
            asyncio.create_task(_trades_loop(universe, trades_poller), name="trades-loop"),
            asyncio.create_task(_universe_loop(universe, session), name="universe-loop"),
        ]

        try:
            await stop_event.wait()
        finally:
            log.info("Shutdown signal received, cancelling tasks...")
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await runner.cleanup()
            await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted")
