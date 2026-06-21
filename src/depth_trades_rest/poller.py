"""Poller for the binance-depth-trades-rest service.

Two sweepers run concurrently:

- :class:`DepthPoller` hits ``/api/v3/depth`` once per symbol every
  ``DEPTH_POLL_S`` seconds and enqueues a hash snapshot to
  :class:`DepthWriter`.

- :class:`TradesPoller` hits ``/api/v3/aggTrades`` once per symbol every
  ``TRADES_POLL_S`` seconds and enqueues the trades to
  :class:`TradesWriter`. We use ``fromId`` from the highest seen trade
  id so a re-poll does not re-emit the same trades.

The symbol universe is fetched from Binance 24h ticker on a long
interval (default 1h) so it tracks volume ranking drift.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Set

import aiohttp

from src.depth_trades_rest.config import (
    DEPTH_LIMIT,
    DEPTH_POLL_S,
    HTTP_INTER_SYMBOL_DELAY_S,
    HTTP_MAX_CONCURRENT,
    HTTP_TIMEOUT_S,
    SYMBOL_REFRESH_S,
    TOP_N,
    TRADES_LIMIT,
    TRADES_POLL_S,
)
from src.depth_trades_rest.redis_writer import DepthWriter, TradesWriter

log = logging.getLogger("depth_trades_rest.poller")

DEPTH_URL = "https://api.binance.com/api/v3/depth"
AGG_TRADES_URL = "https://api.binance.com/api/v3/aggTrades"
TICKER_24H_URL = "https://api.binance.com/api/v3/ticker/24hr"


class SymbolUniverse:
    """Track the top-N USDT symbols by 24h volume, refreshed hourly."""

    def __init__(self) -> None:
        self._symbols: List[str] = []
        self._last_refresh = 0.0
        self._lock = asyncio.Lock()

    @property
    def symbols(self) -> List[str]:
        return list(self._symbols)

    async def refresh(self, session: aiohttp.ClientSession, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._last_refresh) < SYMBOL_REFRESH_S and self._symbols:
            return
        async with self._lock:
            try:
                async with session.get(TICKER_24H_URL, timeout=HTTP_TIMEOUT_S) as resp:
                    resp.raise_for_status()
                    rows = await resp.json()
            except Exception as exc:
                log.warning("[universe] refresh failed: %s", exc)
                return
            usdt = [r for r in rows if r.get("symbol", "").endswith("USDT") and not r.get("symbol", "").endswith(("BUSDUSDT", "TUSDUSDT", "USDCUSDT", "FDUSDUSDT"))]
            usdt.sort(key=lambda r: float(r.get("quoteVolume", 0)), reverse=True)
            new_symbols = [r["symbol"] for r in usdt[:TOP_N]]
            if new_symbols:
                self._symbols = new_symbols
                self._last_refresh = time.monotonic()
                log.info("[universe] refreshed: top-%d USDT symbols by quoteVolume", len(new_symbols))


class DepthPoller:
    # Class-level 429 backoff (shared across all symbol fetches in the sweep)
    _consecutive_429_backoff: float = 0.0
    _last_429: float = 0.0

    def __init__(self, session: aiohttp.ClientSession, universe: SymbolUniverse, writer: DepthWriter) -> None:
        self._session = session
        self._universe = universe
        self._writer = writer
        self._sem = asyncio.Semaphore(HTTP_MAX_CONCURRENT)
        self._last_sweep_end = 0.0
        self._stats: Dict[str, int] = {"ok": 0, "err": 0}

    async def _fetch_one(self, symbol: str) -> Optional[dict]:
        params = {"symbol": symbol, "limit": DEPTH_LIMIT}
        # Back off if we've been hitting 429s recently
        backoff = DepthPoller._consecutive_429_backoff
        if backoff > 0:
            await asyncio.sleep(backoff)
        try:
            async with self._sem:
                async with self._session.get(DEPTH_URL, params=params, timeout=HTTP_TIMEOUT_S) as resp:
                    if resp.status == 429:
                        # Increase shared backoff so subsequent calls slow down
                        DepthPoller._consecutive_429_backoff = min(2.0, backoff * 1.5 + 0.1)
                        DepthPoller._last_429 = time.monotonic()
                        log.warning("[depth] 429 rate-limited on %s (backoff=%.2fs)", symbol, DepthPoller._consecutive_429_backoff)
                        return None
                    DepthPoller._consecutive_429_backoff = 0.0
                    resp.raise_for_status()
                    payload = await resp.json()
        except Exception as exc:
            log.debug("[depth] fetch %s: %s", symbol, exc)
            self._stats["err"] += 1
            return None
        bids = [[float(p), float(q)] for p, q in payload.get("bids", [])]
        asks = [[float(p), float(q)] for p, q in payload.get("asks", [])]
        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        spread = round(best_ask - best_bid, 8) if best_bid and best_ask else 0.0
        self._stats["ok"] += 1
        return {
            "bids": bids,
            "asks": asks,
            "spread": spread,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "event_time": int(time.time() * 1000),
        }

    async def sweep(self) -> int:
        symbols = self._universe.symbols
        if not symbols:
            return 0
        tasks = [self._fetch_one(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        for s, snap in zip(symbols, results):
            if snap is not None:
                self._writer.enqueue(s, snap)
        flushed = await self._writer.flush(force=True)
        self._last_sweep_end = time.monotonic()
        return flushed

    @property
    def is_stale(self) -> bool:
        if self._last_sweep_end == 0.0:
            return True
        return (time.monotonic() - self._last_sweep_end) > (DEPTH_POLL_S * 3)

    @property
    def stats(self) -> Dict[str, int]:
        return self._stats


class TradesPoller:
    # Class-level 429 backoff (shared across all symbol fetches in the sweep)
    _consecutive_429_backoff: float = 0.0

    def __init__(self, session: aiohttp.ClientSession, universe: SymbolUniverse, writer: TradesWriter) -> None:
        self._session = session
        self._universe = universe
        self._writer = writer
        self._sem = asyncio.Semaphore(HTTP_MAX_CONCURRENT)
        self._last_id: Dict[str, int] = {}
        self._last_sweep_end = 0.0
        self._stats: Dict[str, int] = {"fetched": 0, "emitted": 0}

    async def _fetch_one(self, symbol: str) -> List[dict]:
        params = {"symbol": symbol, "limit": TRADES_LIMIT}
        last_id = self._last_id.get(symbol, 0)
        if last_id > 0:
            params["fromId"] = last_id + 1
        backoff = TradesPoller._consecutive_429_backoff
        if backoff > 0:
            await asyncio.sleep(backoff)
        try:
            async with self._sem:
                async with self._session.get(AGG_TRADES_URL, params=params, timeout=HTTP_TIMEOUT_S) as resp:
                    if resp.status == 429:
                        TradesPoller._consecutive_429_backoff = min(2.0, backoff * 1.5 + 0.1)
                        log.warning("[trades] 429 rate-limited on %s (backoff=%.2fs)", symbol, TradesPoller._consecutive_429_backoff)
                        return []
                    TradesPoller._consecutive_429_backoff = 0.0
                    resp.raise_for_status()
                    rows = await resp.json()
        except Exception as exc:
            log.debug("[trades] fetch %s: %s", symbol, exc)
            return []
        if not rows:
            return []
        # Update watermark. aggTrades IDs are strictly increasing per symbol.
        self._last_id[symbol] = int(rows[-1].get("a", last_id))
        self._stats["fetched"] += len(rows)
        self._stats["emitted"] += len(rows)
        return rows

    async def sweep(self) -> int:
        symbols = self._universe.symbols
        if not symbols:
            return 0
        tasks = [self._fetch_one(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        for s, rows in zip(symbols, results):
            if rows:
                self._writer.enqueue(s, rows)
        flushed = await self._writer.flush(force=True)
        self._last_sweep_end = time.monotonic()
        return flushed

    @property
    def is_stale(self) -> bool:
        if self._last_sweep_end == 0.0:
            return True
        return (time.monotonic() - self._last_sweep_end) > (TRADES_POLL_S * 3)

    @property
    def stats(self) -> Dict[str, int]:
        return self._stats
