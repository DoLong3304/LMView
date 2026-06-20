"""Configuration for binance-kline-rest service.

Loads top USDT symbols by 24h quote volume from Binance REST (same source
as ``src/ticker_ws/config.py``) and exposes poll cadence / Redis / rate
limit knobs via environment.

Rate-limit budget (Binance): 1200 weight/min per IP. ``/api/v3/klines``
costs 2 weight regardless of ``limit``. With 100 symbols polled every
30s = 200 calls/min = 400 weight/min ≈ 33% of budget — safe. Adding 1s
polling doubles calls for the 1s-enabled subset.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List

import aiohttp

log = logging.getLogger(__name__)

# ── Binance REST endpoints ────────────────────────────────────────────────

KLINES_URL = os.environ.get(
    "KLINE_REST_KLINES_URL", "https://api.binance.com/api/v3/klines"
)
TICKER_24H_URL = os.environ.get(
    "KLINE_REST_TICKER_URL", "https://api.binance.com/api/v3/ticker/24hr"
)

# ── Symbol discovery ──────────────────────────────────────────────────────

TOP_N = int(os.environ.get("KLINE_REST_TOP_N", "100"))
SYMBOL_REFRESH_SEC = int(os.environ.get("KLINE_REST_SYMBOL_REFRESH_SEC", "3600"))
# Stablecoin / fiat quoted pairs we never want as base candles.
SYMBOL_BLACKLIST_PREFIXES = tuple(
    p.strip() for p in os.environ.get(
        "KLINE_REST_SYMBOL_BLACKLIST",
        "USDC,FDUSD,TUSDC,USDP,USD1,EUR,GBP,TRY,AEUR,EURI,USDS",
    ).split(",") if p.strip()
)

# ── Poll cadence ──────────────────────────────────────────────────────────

# How often (seconds) each symbol's 1m window is re-fetched. 30s means the
# forming 1m candle refreshes every 30s and the just-closed candle lands
# within 30s of close. Binance 1m candles close on :00 of each minute.
POLL_INTERVAL_1M_S = int(os.environ.get("KLINE_REST_POLL_1M_S", "30"))
# 1s candles are heavier (1 call/s per symbol). Default disabled; enable
# for a small curated set via KLINE_REST_1M_SYMBOLS.
ENABLE_1S = os.environ.get("KLINE_REST_ENABLE_1S", "false").lower() in (
    "1", "true", "yes", "on",
)
POLL_INTERVAL_1S_S = int(os.environ.get("KLINE_REST_POLL_1S_S", "5"))
LIMIT_1M = int(os.environ.get("KLINE_REST_LIMIT_1M", "100"))  # candles per fetch
LIMIT_1S = int(os.environ.get("KLINE_REST_LIMIT_1S", "60"))

# ── Rate limiting ─────────────────────────────────────────────────────────

# Hard cap on concurrent in-flight REST requests. Binance weight is per-IP,
# not per-connection, so concurrency itself doesn't change weight usage, but
# bounding it protects memory + avoids burst timeouts.
MAX_CONCURRENT = int(os.environ.get("KLINE_REST_MAX_CONCURRENT", "20"))
REQUEST_TIMEOUT_S = float(os.environ.get("KLINE_REST_TIMEOUT_S", "15"))
RETRY_ATTEMPTS = int(os.environ.get("KLINE_REST_RETRY_ATTEMPTS", "3"))
RETRY_BACKOFF_BASE_S = float(os.environ.get("KLINE_REST_RETRY_BACKOFF_S", "1.0"))
# Sleep between symbols within a sweep (avoids a 100-req burst).
INTER_SYMBOL_DELAY_S = float(os.environ.get("KLINE_REST_INTER_SYMBOL_DELAY_S", "0.05"))

# ── Redis ─────────────────────────────────────────────────────────────────

REDIS_SENTINELS = os.environ.get(
    "REDIS_SENTINELS",
    "redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379",
)
REDIS_MASTER_NAME = os.environ.get("REDIS_MASTER_NAME", "mymaster")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-master")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

# Retention must match keydb_kline.py so we don't shorten existing TTLs.
TTL_1M_S = max(int(os.environ.get("KEYDB_1M_RETENTION_DAYS", "7")), 1) * 86_400
TTL_1S_S = max(int(os.environ.get("KEYDB_1S_RETENTION_DAYS", "1")), 1) * 86_400

# ── Batched Redis writer ──────────────────────────────────────────────────

REDIS_FLUSH_MS = int(os.environ.get("KLINE_REST_REDIS_FLUSH_MS", "500"))
REDIS_FLUSH_MAX_BUFFER = int(os.environ.get("KLINE_REST_REDIS_BUFFER_MAX", "5000"))

# ── HTTP / metrics ────────────────────────────────────────────────────────

METRICS_HOST = os.environ.get("METRICS_HOST", "0.0.0.0")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9101"))


@dataclass
class KlineConfig:
    """Resolved symbol list (loaded once, refreshed hourly)."""

    top_symbols: List[str] = field(default_factory=list)

    @classmethod
    async def load(cls, session: aiohttp.ClientSession) -> "KlineConfig":
        """Fetch top USDT symbols by 24h quote volume from Binance REST."""
        log.info("Loading top %d USDT symbols from %s", TOP_N, TICKER_24H_URL)
        async with session.get(TICKER_24H_URL) as resp:
            resp.raise_for_status()
            rows = await resp.json()

        filtered = [
            r for r in rows
            if r.get("symbol", "").endswith("USDT")
            and not any(r["symbol"].startswith(p) for p in SYMBOL_BLACKLIST_PREFIXES)
            and r.get("quoteVolume") not in (None, "", "0", "0.0")
        ]
        filtered.sort(key=lambda r: float(r.get("quoteVolume") or 0), reverse=True)
        symbols = [r["symbol"] for r in filtered[:TOP_N]]
        log.info("Loaded %d USDT pairs (top by 24h quoteVolume)", len(symbols))
        return cls(top_symbols=symbols)
