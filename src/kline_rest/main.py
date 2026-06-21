"""Entrypoint for binance-kline-rest Swarm service.

Long-term replacement for the dead producer's kline WebSocket path
(Binance WS is 403-geofenced from this AWS region; REST is not) and
for the cron-based stopgap ``scripts/cron_refresh_klines.sh``.

Architecture:
    - ``KlinePoller`` sweeps the top-N USDT symbol list every
      ``POLL_INTERVAL_1M_S``, fetching ``LIMIT_1M`` candles per symbol
      from ``api.binance.com/api/v3/klines``.
    - Fetched candles → ``KlineRedisWriter`` (batched pipeline) → Redis
      in the canonical shape (``candle:{interval}:binance:{symbol}`` +
      ``candle:latest:binance:{symbol}``).
    - Prometheus metrics on ``:METRICS_PORT/metrics``.
    - Health on ``:METRICS_PORT/healthz`` — reports OK only if the last
      successful 1m sweep is fresher than ``2 * POLL_INTERVAL_1M_S``
      (so Docker healthcheck can detect a stalled poller).

Symbol list is refreshed hourly from Binance 24h ticker to track volume
ranking drift.
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
    Histogram,
    generate_latest,
)
import redis.asyncio as redis_async

# Ensure /app and /app/src are on sys.path when running inside the
# container. The Dockerfile copies /src to /app/src, so:
#   /app/src/kline_rest/main.py  →  /app/src/kline_rest  →  ..  →  /app/src
#   /app/src/kline_rest/main.py  →  /app/src/kline_rest  →  ..  →  /app/src
#                                  →  ..  →  /app
# Some modules (``src.common.kafka_client``) import the un-namespaced
# ``common`` alias, so we register /app/src as well.
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/src",
)

# Alias ``common`` → ``src.common`` so the un-namespaced imports in
# ``src.common.kafka_client`` (e.g. ``from common.config import …``)
# resolve when this service runs from /app/src.
import importlib
_common_pkg = importlib.import_module("src.common")
sys.modules["common"] = _common_pkg
sys.modules["common.config"] = importlib.import_module("src.common.config")
sys.modules["common.kafka_client"] = importlib.import_module("src.common.kafka_client")
sys.modules["common.avro_serializer"] = importlib.import_module("src.common.avro_serializer")

from src.common.avro_serializer import AvroSerializer  # noqa: E402
from src.common.kafka_client import init_producer, send_to_kafka  # noqa: E402

KAFKA_TOPIC_KLINES = os.environ.get("KAFKA_TOPIC_KLINES", "crypto_klines")
SCHEMA_REGISTRY_URL = os.environ.get(
    "SCHEMA_REGISTRY_URL", "http://schema-registry:8080/apis/ccompat/v7"
)

KAFKA_TOPIC_KLINES = os.environ.get("KAFKA_TOPIC_KLINES", "crypto_klines")
SCHEMA_REGISTRY_URL = os.environ.get(
    "SCHEMA_REGISTRY_URL", "http://schema-registry:8080/apis/ccompat/v7"
)

from src.kline_rest.config import (  # noqa: E402
    METRICS_HOST,
    METRICS_PORT,
    POLL_INTERVAL_1M_S,
    REDIS_HOST,
    REDIS_MASTER_NAME,
    REDIS_PORT,
    REDIS_DB,
    REDIS_SENTINELS,
    SYMBOL_REFRESH_SEC,
    KlineConfig,
)
from src.common.avro_serializer import AvroSerializer  # noqa: E402
from src.common.kafka_client import init_producer, send_to_kafka  # noqa: E402
from src.kline_rest.poller import (  # noqa: E402
    KlinePoller,
    RateLimiter,
    set_avro_serializer,
)
from src.kline_rest.redis_writer import KlineRedisWriter  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
log = logging.getLogger("binance-kline-rest")

# ── Prometheus metrics ────────────────────────────────────────────────────

SWEEPS_1M = Counter("kline_rest_sweeps_1m_total", "1m poll sweeps completed")
SWEEPS_1S = Counter("kline_rest_sweeps_1s_total", "1s poll sweeps completed")
CANDLES_1M = Counter("kline_rest_candles_1m_total", "1m candles written")
CANDLES_1S = Counter("kline_rest_candles_1s_total", "1s candles written")
ERRORS = Counter("kline_rest_errors_total", "Total poll errors")
RATE_LIMITED = Counter("kline_rest_rate_limited_total", "Binance 429/418 hits")
SYMBOLS_TRACKED = Gauge("kline_rest_symbols_tracked", "Symbols in active poll list")
LAST_SWEEP_1M_AGE = Gauge(
    "kline_rest_last_sweep_1m_age_seconds",
    "Seconds since last successful 1m sweep",
)
REDIS_BUFFER = Gauge("kline_rest_redis_buffer_size", "Pending kline writes in buffer")
HEALTHY = Gauge("kline_rest_healthy", "1 if service is healthy, 0 otherwise")
SWEEP_LATENCY = Histogram(
    "kline_rest_sweep_1m_seconds",
    "1m sweep wall-clock duration",
    buckets=(1, 5, 10, 20, 30, 60, 120),
)

# ── Globals shared with HTTP handlers ─────────────────────────────────────

STARTED_AT = time.time()
POLLER: KlinePoller | None = None
WRITER: KlineRedisWriter | None = None


# ── Redis connection (Sentinel-aware, fallback to direct) ───────────────

async def get_redis() -> redis_async.Redis:
    """Build Redis async client (master-only for writes)."""
    sentinel_nodes = [
        tuple(n.split(":")) for n in REDIS_SENTINELS.split(",") if n.strip()
    ]
    try:
        from redis.asyncio.sentinel import Sentinel as AsyncSentinel
        sentinel = AsyncSentinel(
            sentinel_nodes, socket_timeout=0.5, socket_connect_timeout=0.5,
        )
        client = sentinel.master_for(
            REDIS_MASTER_NAME,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
            decode_responses=False,
            max_connections=64,
        )
        await client.ping()
        log.info("Redis connected via Sentinel (%s)", REDIS_MASTER_NAME)
        return client
    except Exception as e:
        log.warning(
            "Sentinel connect failed (%s), fallback to direct %s:%d",
            e, REDIS_HOST, REDIS_PORT,
        )
        client = redis_async.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=False, socket_keepalive=True,
            health_check_interval=30, max_connections=64,
        )
        await client.ping()
        log.info("Redis connected via direct %s:%d", REDIS_HOST, REDIS_PORT)
        return client


# ── Health / metrics HTTP server ──────────────────────────────────────────


def _is_healthy() -> bool:
    """Healthy = last 1m sweep within 2× poll interval (and startup grace)."""
    if POLLER is None:
        return False
    # Grace period during startup: allow 3× poll interval before requiring a sweep.
    startup_grace = max(3 * POLL_INTERVAL_1M_S, 90)
    if time.time() - STARTED_AT < startup_grace:
        return True
    age = POLLER.stats.get("last_sweep_1m_age_s")
    if age is None:
        return False
    return age < (2 * POLL_INTERVAL_1M_S)


async def metrics_handler(request: web.Request) -> web.Response:
    # Reflect live state into gauges before scraping.
    if POLLER is not None:
        s = POLLER.stats
        SYMBOLS_TRACKED.set(s.get("symbols", 0))
        if s.get("last_sweep_1m_age_s") is not None:
            LAST_SWEEP_1M_AGE.set(s["last_sweep_1m_age_s"])
    if WRITER is not None:
        REDIS_BUFFER.set(len(WRITER._buffer))
    HEALTHY.set(1 if _is_healthy() else 0)
    # aiohttp rejects a content_type containing "; charset", but
    # prometheus_client.CONTENT_TYPE_LATEST includes it. Set via headers.
    body = generate_latest()
    return web.Response(
        body=body,
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )


async def healthz_handler(request: web.Request) -> web.Response:
    healthy = _is_healthy()
    status_code = 200 if healthy else 503
    body = {
        "ok": healthy,
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "poller": POLLER.stats if POLLER is not None else None,
        "writer": WRITER.stats if WRITER is not None else None,
    }
    return web.json_response(body, status=status_code)


async def start_http() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/healthz", healthz_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, METRICS_HOST, METRICS_PORT)
    await site.start()
    log.info(
        "HTTP server on http://%s:%d (metrics, healthz)", METRICS_HOST, METRICS_PORT,
    )
    return runner


# ── Symbol refresh task ───────────────────────────────────────────────────


async def symbol_refresher(
    poller: KlinePoller, session: aiohttp.ClientSession, stop_event: asyncio.Event,
) -> None:
    """Hourly re-fetch the top-N symbol list to track volume drift."""
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=SYMBOL_REFRESH_SEC,
            )
            return
        except asyncio.TimeoutError:
            pass
        try:
            cfg = await KlineConfig.load(session)
            if cfg.top_symbols:
                poller._symbols = cfg.top_symbols
                log.info(
                    "[symbols] refreshed: %d symbols", len(cfg.top_symbols),
                )
        except Exception as e:
            log.warning("[symbols] refresh failed: %s", e)


# ── Metric-bridge task ────────────────────────────────────────────────────


async def metric_bridge(poller: KlinePoller, writer: KlineRedisWriter) -> None:
    """Sample poller/writer counters into Prometheus each 5s."""
    prev = None
    while True:
        await asyncio.sleep(5)
        s = poller.stats
        if prev is not None:
            SWEEPS_1M.inc(max(0, s["sweeps_1m"] - prev["sweeps_1m"]))
            SWEEPS_1S.inc(max(0, s["sweeps_1s"] - prev["sweeps_1s"]))
            CANDLES_1M.inc(max(0, s["candles_1m"] - prev["candles_1m"]))
            CANDLES_1S.inc(max(0, s["candles_1s"] - prev["candles_1s"]))
            ERRORS.inc(max(0, s["errors"] - prev["errors"]))
            RATE_LIMITED.inc(max(0, s["rate_limited"] - prev["rate_limited"]))
        SYMBOLS_TRACKED.set(s["symbols"])
        if s.get("last_sweep_1m_age_s") is not None:
            LAST_SWEEP_1M_AGE.set(s["last_sweep_1m_age_s"])
        REDIS_BUFFER.set(len(writer._buffer))
        HEALTHY.set(1 if _is_healthy() else 0)
        prev = s


# ── Main ──────────────────────────────────────────────────────────────────


async def main() -> None:
    global POLLER, WRITER

    stop_event = asyncio.Event()

    # 1. Redis
    redis = await get_redis()
    log.info("Redis OK")
    writer = KlineRedisWriter(redis)
    await writer.start()
    WRITER = writer

    # 2. Shared HTTP session + initial symbol load
    timeout = aiohttp.ClientTimeout(total=15)
    session = aiohttp.ClientSession(timeout=timeout)
    try:
        cfg = await KlineConfig.load(session)
    except Exception as e:
        log.error("Initial symbol load failed: %s — retrying in 30s", e)
        await asyncio.sleep(30)
        cfg = await KlineConfig.load(session)
    symbols: List[str] = cfg.top_symbols
    log.info("Config: %d symbols, 1m poll every %ds", len(symbols), POLL_INTERVAL_1M_S)

    # 3. HTTP server
    await start_http()

    # 3.5 Initialize Kafka producer + Avro serializer so the poller can
    # mirror closed candles to the crypto_klines topic that feeds the
    # Spark lakehouse (Binance @kline WS is geofenced from AWS us-east-1).
    try:
        import os as _os
        # The schema file lives at <repo>/schemas/kline.avsc. The container
        # WORKDIR is /app, so the file is at /app/schemas/kline.avsc. The
        # repo path resolves as:
        #   /app/src/kline_rest/main.py  →  /app/src/kline_rest  →  ..
        #   → /app/src  →  ..  → /app  →  /app/schemas
        schema_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
            "schemas",
            "kline.avsc",
        )
        avro = AvroSerializer(SCHEMA_REGISTRY_URL)
        avro.register(KAFKA_TOPIC_KLINES, schema_path)
        set_avro_serializer(avro)
        init_producer()
        log.info("Kafka producer + Avro ready: topic=%s schema=%s", KAFKA_TOPIC_KLINES, schema_path)
    except Exception as exc:
        log.warning("Kafka init failed (will skip Kafka publish): %s", exc)

    # 4. Poller
    rate_limiter = RateLimiter()
    async with KlinePoller(writer, rate_limiter, symbols) as poller:
        POLLER = poller

        loop1m = asyncio.create_task(poller.run_1m_loop(stop_event), name="kline-1m")
        loop1s = asyncio.create_task(poller.run_1s_loop(stop_event), name="kline-1s")
        sym_task = asyncio.create_task(
            symbol_refresher(poller, session, stop_event), name="sym-refresh",
        )
        bridge_task = asyncio.create_task(metric_bridge(poller, writer), name="metrics")

        # 5. Wait for shutdown signal
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
            log.info("stopping poller tasks...")
            stop_event.set()
            await asyncio.gather(loop1m, loop1s, sym_task, return_exceptions=True)
            bridge_task.cancel()
            try:
                await bridge_task
            except asyncio.CancelledError:
                pass
            await writer.stop()
            await session.close()
            await redis.close()
            log.info("bye")


if __name__ == "__main__":
    asyncio.run(main())
