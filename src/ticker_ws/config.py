"""Configuration for binance-ticker-ws service.

Loads top USDT symbols by 24h quote volume from Binance REST, splits into
``TICKER_WS_SHARDS`` shards with at most ``TICKER_WS_SYMBOLS_PER_SHARD``
streams each (Binance rate limit safe).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List

import aiohttp

log = logging.getLogger(__name__)

# ── Environment defaults ──────────────────────────────────────────────────

EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/ticker/24hr"
SYMBOL_REFRESH_SEC = int(os.environ.get("TICKER_WS_SYMBOL_REFRESH_SEC", "3600"))
SHARDS = int(os.environ.get("TICKER_WS_SHARDS", "8"))
SYMBOLS_PER_SHARD = int(os.environ.get("TICKER_WS_SYMBOLS_PER_SHARD", "100"))
TOP_N = int(os.environ.get("TICKER_WS_TOP_N", "671"))

# Binance WS endpoint base
WS_BASE = os.environ.get("TICKER_WS_BASE", "wss://stream.binance.com:9443/stream")

# Reconnect / heartbeat
RECONNECT_BASE_MS = int(os.environ.get("TICKER_WS_RECONNECT_BASE_MS", "1000"))
RECONNECT_MAX_MS = int(os.environ.get("TICKER_WS_RECONNECT_MAX_MS", "30000"))
PING_INTERVAL_S = int(os.environ.get("TICKER_WS_PING_INTERVAL_S", "30"))
PING_TIMEOUT_S = int(os.environ.get("TICKER_WS_PING_TIMEOUT_S", "10"))

# Redis
REDIS_KEY_TTL_S = int(os.environ.get("TICKER_WS_TTL_S", "300"))
REDIS_FLUSH_MS = int(os.environ.get("TICKER_WS_REDIS_FLUSH_MS", "50"))
REDIS_FLUSH_MAX_BUFFER = int(os.environ.get("TICKER_WS_REDIS_BUFFER_MAX", "2000"))


@dataclass
class TickerConfig:
    """Resolved ticker configuration (loaded once at startup, refreshed hourly)."""

    shards: List[List[str]] = field(default_factory=list)
    top_symbols: List[str] = field(default_factory=list)

    @property
    def total_symbols(self) -> int:
        return sum(len(s) for s in self.shards)

    @classmethod
    async def load(cls) -> "TickerConfig":
        """Fetch top USDT symbols from Binance REST and split into shards."""
        log.info("Loading top %d USDT symbols from %s", TOP_N, EXCHANGE_INFO_URL)
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(EXCHANGE_INFO_URL) as resp:
                resp.raise_for_status()
                rows = await resp.json()

        # Filter USDT pairs, sort by 24h quote volume desc, take top N
        usdt_rows = [
            r for r in rows
            if r.get("symbol", "").endswith("USDT")
            and r.get("quoteVolume") not in (None, "", "0", "0.0")
        ]
        usdt_rows.sort(key=lambda r: float(r.get("quoteVolume") or 0), reverse=True)
        symbols = [r["symbol"] for r in usdt_rows[:TOP_N]]
        log.info("Loaded %d USDT pairs (top by 24h quoteVolume)", len(symbols))

        # Split into shards, each capped at SYMBOLS_PER_SHARD
        shards: List[List[str]] = []
        for i in range(0, len(symbols), SYMBOLS_PER_SHARD):
            shards.append(symbols[i : i + SYMBOLS_PER_SHARD])

        # Pad shards to ensure we have SHARDS shards; if symbol list is smaller
        # than SHARDS × SYMBOLS_PER_SHARD, distribute evenly
        if len(symbols) > 0 and len(shards) < SHARDS and len(shards) > 0:
            # Re-distribute evenly across SHARDS shards
            n = len(symbols)
            per = (n + SHARDS - 1) // SHARDS  # ceil
            shards = [symbols[i : i + per] for i in range(0, n, per)]
            shards = shards[:SHARDS]

        log.info(
            "Shard layout: %d shards, sizes=%s (total=%d symbols)",
            len(shards),
            [len(s) for s in shards],
            sum(len(s) for s in shards),
        )

        return cls(shards=shards, top_symbols=symbols)

    def shard_url(self, shard_id: int) -> str:
        """Build combined-stream WS URL for the given shard."""
        if shard_id >= len(self.shards):
            raise IndexError(f"shard_id {shard_id} out of range ({len(self.shards)})")
        streams = "/".join(f"{s.lower()}@ticker" for s in self.shards[shard_id])
        return f"{WS_BASE}?streams={streams}"