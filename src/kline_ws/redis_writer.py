"""Batched Redis writer for 1s kline updates.

Buffers ZADD + ZREMRANGEBYSCORE + EXPIRE calls in memory, flushes via
pipeline every ``REDIS_FLUSH_MS`` or when buffer exceeds threshold.

Writes to ``candle:1s:binance:{symbol}`` sorted set — exact same key shape
as ``DirectRedisWriter.write_kline()`` and ``keydb_kline.py``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Dict, List, Tuple

from redis.asyncio import Redis

from src.kline_ws.config import REDIS_FLUSH_MAX_BUFFER, REDIS_FLUSH_MS, REDIS_KEY_TTL_S

log = logging.getLogger(__name__)

EXCHANGE = "binance"


class KlineWsRedisWriter:
    """Buffer and pipeline-write 1s kline updates to Redis sorted sets.

    Dedup key: (symbol, open_time_ms) — if multiple WS frames for the same
    candle arrive within one flush window, only the last is kept (ZADD
    with same score overwrites the member in Redis).
    """

    CLEANUP_EVERY = 60  # trim old members every N writes per key

    def __init__(self, redis: Redis):
        self._r = redis
        self._buffer: Dict[Tuple[str, int], dict] = {}  # (symbol, open_ms) -> kline_item
        self._flush_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._flush_count = 0
        self._write_count = 0
        self._last_flush_at = 0.0
        # Per-key write counter for periodic cleanup
        self._write_counts: Dict[str, int] = {}

    def add(self, item: dict) -> None:
        """Buffer one kline item. Overwrites earlier item for same candle."""
        key = (item["symbol"], item["kline_start"])
        self._buffer[key] = item
        if len(self._buffer) >= REDIS_FLUSH_MAX_BUFFER:
            asyncio.create_task(self.flush())

    async def start(self) -> None:
        self._stop_event.clear()
        self._flush_task = asyncio.create_task(self._flush_loop(), name="kline-ws-flush")

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
                log.warning("[kline-ws-writer] flush error: %s", e)

    async def flush(self) -> None:
        """Flush buffered writes via a single Redis pipeline."""
        if not self._buffer:
            return

        items: List[dict] = list(self._buffer.values())
        self._buffer.clear()

        try:
            pipe = self._r.pipeline(transaction=False)
            for item in items:
                symbol = item["symbol"]
                exchange = item["exchange"]
                kline_start = item["kline_start"]
                candle_json = item["candle_json"]
                history_key = f"candle:1s:{exchange}:{symbol}"

                # Dedup: remove old member at same score before ZADD
                pipe.zremrangebyscore(history_key, kline_start, kline_start)
                pipe.zadd(history_key, {candle_json: float(kline_start)})
                pipe.expire(history_key, REDIS_KEY_TTL_S)

                # Periodic cleanup: trim members older than 2x TTL
                ck = history_key
                cnt = self._write_counts.get(ck, 0) + 1
                self._write_counts[ck] = cnt
                if cnt % self.CLEANUP_EVERY == 0:
                    cutoff_ms = int(time.time() * 1000) - REDIS_KEY_TTL_S * 1000
                    pipe.zremrangebyscore(history_key, 0, cutoff_ms)

            await pipe.execute()
            self._flush_count += 1
            self._write_count += len(items)
            self._last_flush_at = time.time()
        except Exception as e:
            log.warning("[kline-ws-writer] pipeline failed (%d items): %s", len(items), e)
            # Re-buffer for retry
            for item in items:
                self._buffer[(item["symbol"], item["kline_start"])] = item

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
        }
