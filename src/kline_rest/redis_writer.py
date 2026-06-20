"""Batched Redis writer for kline updates.

Mirrors ``src/ticker_ws/redis_writer.py``: buffers ZADD + HSET + EXPIRE
calls, flushes via pipeline every ``REDIS_FLUSH_MS`` or when buffer fills.

Writes the canonical LMView candle shape produced by
``src/processing/writers/keydb_kline.py``:

    History (sorted set):
        ZADD candle:{interval}:{exchange}:{symbol} {open_time_ms} '{json}'
        EXPIRE candle:{interval}:{exchange}:{symbol} {ttl}
    where json = {"t","o","h","l","c","v","qv","n","x"} (compact)

    Latest (hash, 1m+ only):
        HSET candle:latest:{exchange}:{symbol} {open,high,...,interval,exchange}
        EXPIRE candle:latest:{exchange}:{symbol} {ttl}

ZADD is idempotent (same member+score), so re-writing a candle that's
already in Redis is a no-op — safe to retry.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from redis.asyncio import Redis

from src.kline_rest.config import REDIS_FLUSH_MAX_BUFFER, REDIS_FLUSH_MS, TTL_1M_S, TTL_1S_S

log = logging.getLogger(__name__)

EXCHANGE = "binance"


@dataclass
class KlineUpdate:
    """One candle ready to write to Redis."""

    symbol: str
    interval: str          # "1m" or "1s"
    open_time_ms: int
    o: float
    h: float
    l: float
    c: float
    v: float
    qv: float
    n: int
    is_closed: bool
    # When True, also HSET candle:latest (only for 1m; 1s skips latest).
    update_latest: bool = False

    @property
    def member_json(self) -> str:
        """Compact JSON matching keydb_kline.py candle payload."""
        return json.dumps(
            {
                "t": self.open_time_ms,
                "o": self.o,
                "h": self.h,
                "l": self.l,
                "c": self.c,
                "v": self.v,
                "qv": self.qv,
                "n": self.n,
                "x": self.is_closed,
            },
            separators=(",", ":"),
        )


class KlineRedisWriter:
    """Buffer and pipeline-write kline updates to Redis.

    Coalescing: if multiple updates for the same (interval, symbol,
    open_time_ms) arrive within one flush window, only the last is kept
    (ZADD member is deterministic; latest-hash is overwritten). This is
    correct because newer = fresher.
    """

    # Every CLEANUP_EVERY writes to a given history key, also trim members
    # older than the TTL window. Mirrors keydb_kline.py and keeps the sorted
    # set bounded to the retention window regardless of how long the service
    # runs. Without this, stale duplicate members from prior writers (e.g.
    # the cron stopgap) would linger until the key's own EXPIRE fires.
    CLEANUP_EVERY = 60

    def __init__(self, redis: Redis):
        self._r = redis
        # Dedupe key: (interval, symbol, open_time_ms) -> KlineUpdate
        self._buffer: Dict[Tuple[str, str, int], KlineUpdate] = {}
        self._flush_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._flush_count = 0
        self._write_count = 0
        self._last_flush_at = 0.0
        self._last_error: str | None = None
        self._last_error_at: float = 0.0
        # Per-(interval,symbol) write counter → drives CLEANUP_EVERY trimming.
        self._write_counts: Dict[Tuple[str, str], int] = {}

    def add(self, update: KlineUpdate) -> None:
        """Buffer a kline update (overwrites earlier update for same candle)."""
        key = (update.interval, update.symbol, update.open_time_ms)
        self._buffer[key] = update
        if len(self._buffer) >= REDIS_FLUSH_MAX_BUFFER:
            asyncio.create_task(self.flush())

    async def start(self) -> None:
        self._stop_event.clear()
        self._flush_task = asyncio.create_task(self._flush_loop(), name="kline-flush")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._flush_task:
            try:
                await asyncio.wait_for(self._flush_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._flush_task.cancel()
        await self.flush()

    async def _flush_loop(self) -> None:
        interval = REDIS_FLUSH_MS / 1000.0
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass
            try:
                await self.flush()
            except Exception as e:
                log.warning("[kline-writer] flush error: %s", e)

    async def flush(self) -> None:
        """Flush buffered writes via a single Redis pipeline."""
        if not self._buffer:
            return

        items: List[KlineUpdate] = list(self._buffer.values())
        self._buffer.clear()

        try:
            pipe = self._r.pipeline(transaction=False)
            for u in items:
                history_key = f"candle:{u.interval}:{EXCHANGE}:{u.symbol}"
                ttl = TTL_1M_S if u.interval != "1s" else TTL_1S_S
                # Dedup: remove any existing member(s) at this score before ZADD.
                # This mirrors keydb_kline.py and preserves the contract documented
                # in AGENTS.md ("remove old sorted-set score before ZADD"). Without
                # it, repeated polls of the forming candle would accumulate
                # duplicate members for the same bucket, causing unbounded sorted-
                # set growth and ambiguous ZRANGE reads.
                pipe.zremrangebyscore(history_key, u.open_time_ms, u.open_time_ms)
                pipe.zadd(history_key, {u.member_json: float(u.open_time_ms)})
                pipe.expire(history_key, ttl)
                if u.update_latest and u.interval != "1s":
                    latest_key = f"candle:latest:{EXCHANGE}:{u.symbol}"
                    pipe.hset(
                        latest_key,
                        mapping={
                            "open":         str(u.o),
                            "high":         str(u.h),
                            "low":          str(u.l),
                            "close":        str(u.c),
                            "volume":       str(u.v),
                            "quote_volume": str(u.qv),
                            "trade_count":  str(u.n),
                            "is_closed":    "1" if u.is_closed else "0",
                            "kline_start":  str(u.open_time_ms),
                            "interval":     u.interval,
                            "exchange":     EXCHANGE,
                        },
                    )
                    pipe.expire(latest_key, ttl)
                # Periodic full-window trim: drop members older than the TTL.
                ck_key = (u.interval, u.symbol)
                ck_count = self._write_counts.get(ck_key, 0) + 1
                self._write_counts[ck_key] = ck_count
                if ck_count % self.CLEANUP_EVERY == 0:
                    # cutoff in ms = now_ms - ttl_s*1000
                    cutoff_ms = int(time.time() * 1000) - ttl * 1000
                    pipe.zremrangebyscore(history_key, 0, cutoff_ms)
            await pipe.execute()
            self._flush_count += 1
            self._write_count += len(items)
            self._last_flush_at = time.time()
        except Exception as e:
            self._last_error = str(e)
            self._last_error_at = time.time()
            log.warning("[kline-writer] pipeline failed (%d items): %s", len(items), e)
            # Re-buffer for retry (avoid data loss)
            for u in items:
                self._buffer[(u.interval, u.symbol, u.open_time_ms)] = u

    @property
    def stats(self) -> dict:
        return {
            "flush_count": self._flush_count,
            "write_count": self._write_count,
            "buffer_size": len(self._buffer),
            "last_flush_age_s": (
                round(time.time() - self._last_flush_at, 3)
                if self._last_flush_at else None
            ),
            "last_error": self._last_error,
            "last_error_age_s": (
                round(time.time() - self._last_error_at, 3)
                if self._last_error_at else None
            ),
        }
