"""Configuration cho binance-kline-ws service.

Load top USDT symbols from Binance REST, chia thành N shards,
build combined-stream URLs cho @kline_1s.

Mô phỏng ``src/ticker_ws/config.py`` nhưng dùng kline_1s thay vì @ticker.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List

import aiohttp

log = logging.getLogger(__name__)

# ── Binance endpoints ────────────────────────────────────────────────────

EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/ticker/24hr"
KLINES_WS_BASE = os.environ.get(
    "KLINE_WS_BASE", "wss://stream.binance.com:9443/stream"
)

# ── Symbol discovery ─────────────────────────────────────────────────────

TOP_N = int(os.environ.get("KLINE_WS_TOP_N", "200"))
SYMBOL_REFRESH_SEC = int(os.environ.get("KLINE_WS_SYMBOL_REFRESH_SEC", "3600"))
SYMBOL_BLACKLIST_PREFIXES = tuple(
    p.strip() for p in os.environ.get(
        "KLINE_WS_SYMBOL_BLACKLIST",
        "USDC,FDUSD,TUSDC,USDP,USD1,EUR,GBP,TRY,AEUR,EURI,USDS",
    ).split(",") if p.strip()
)

# ── Shard config ─────────────────────────────────────────────────────────

SHARDS = int(os.environ.get("KLINE_WS_SHARDS", "8"))
SYMBOLS_PER_SHARD = int(os.environ.get("KLINE_WS_SYMBOLS_PER_SHARD", "100"))

# ── WebSocket ────────────────────────────────────────────────────────────

PING_INTERVAL_S = int(os.environ.get("KLINE_WS_PING_INTERVAL_S", "30"))
PING_TIMEOUT_S = int(os.environ.get("KLINE_WS_PING_TIMEOUT_S", "10"))
RECONNECT_BASE_MS = int(os.environ.get("KLINE_WS_RECONNECT_BASE_MS", "1000"))
RECONNECT_MAX_MS = int(os.environ.get("KLINE_WS_RECONNECT_MAX_MS", "30000"))

# ── Redis ────────────────────────────────────────────────────────────────

REDIS_KEY_TTL_S = int(os.environ.get("KLINE_WS_TTL_S", "86400"))  # 1 day
REDIS_FLUSH_MS = int(os.environ.get("KLINE_WS_REDIS_FLUSH_MS", "50"))
REDIS_FLUSH_MAX_BUFFER = int(os.environ.get("KLINE_WS_REDIS_BUFFER_MAX", "2000"))

# ── HTTP / metrics ───────────────────────────────────────────────────────

METRICS_HOST = os.environ.get("METRICS_HOST", "0.0.0.0")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9102"))


@dataclass
class KlineWsConfig:
    """Resolved kline WebSocket configuration."""

    shards: List[List[str]] = field(default_factory=list)
    top_symbols: List[str] = field(default_factory=list)

    @property
    def total_symbols(self) -> int:
        return sum(len(s) for s in self.shards)

    def shard_url(self, shard_idx: int) -> str:
        """Build combined-stream URL for one shard's symbols."""
        if shard_idx < 0 or shard_idx >= len(self.shards):
            raise IndexError(f"shard_idx {shard_idx} out of range")
        streams = [f"{s.lower()}@kline_1s" for s in self.shards[shard_idx]]
        return f"{KLINES_WS_BASE}?streams={'/'.join(streams)}"

    @classmethod
    async def load(cls) -> "KlineWsConfig":
        """Fetch top USDT symbols, split into shards."""
        log.info("Loading top %d USDT symbols from %s", TOP_N, EXCHANGE_INFO_URL)
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(EXCHANGE_INFO_URL) as resp:
                resp.raise_for_status()
                rows = await resp.json()

        usdt_rows = [
            r for r in rows
            if r.get("symbol", "").endswith("USDT")
            and r.get("quoteVolume") not in (None, "", "0", "0.0")
            and not any(r["symbol"].startswith(p) for p in SYMBOL_BLACKLIST_PREFIXES)
        ]
        usdt_rows.sort(key=lambda r: float(r.get("quoteVolume") or 0), reverse=True)
        symbols = [r["symbol"] for r in usdt_rows[:TOP_N]]
        log.info("Loaded %d USDT pairs (top by 24h quoteVolume)", len(symbols))

        # Split into shards
        shards: List[List[str]] = []
        n = len(symbols)
        per = max(1, (n + SHARDS - 1) // SHARDS)
        for i in range(0, n, per):
            shards.append(symbols[i:i + per])
        # Pad to SHARDS if needed
        while len(shards) < SHARDS:
            shards.append([])

        cfg = cls(top_symbols=symbols, shards=shards)
        log.info("Split into %d shards (%d symbols total)", len(shards), cfg.total_symbols)
        return cfg
