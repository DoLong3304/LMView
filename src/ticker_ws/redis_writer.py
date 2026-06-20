"""Batched Redis writer for ticker updates.

Buffers HSET + EXPIRE calls in memory, flushes via pipeline every
``REDIS_FLUSH_MS`` or whenever buffer exceeds ``REDIS_FLUSH_MAX_BUFFER``.
Uses Redis Sentinel-aware connection from ``common.flink_redis_sentinel``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Tuple

from redis.asyncio import Redis

from src.ticker_ws.config import REDIS_FLUSH_MAX_BUFFER, REDIS_FLUSH_MS, REDIS_KEY_TTL_S

log = logging.getLogger(__name__)


class TickerRedisWriter:
    """Buffer and pipeline-write ticker updates to Redis."""

    def __init__(self, redis: Redis):
        self._r = redis
        self._buffer: Dict[str, Dict[str, str]] = {}  # key -> mapping
        self._flush_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._flush_count = 0
        self._write_count = 0
        self._last_flush_at = 0.0

    def add(self, key: str, mapping: Dict[str, str]) -> None:
        """Buffer a HSET. Overwrites previous unsent mapping for the same key."""
        self._buffer[key] = mapping
        if len(self._buffer) >= REDIS_FLUSH_MAX_BUFFER:
            # Fire and forget; the flush loop will pick it up
            asyncio.create_task(self.flush())

    async def start(self) -> None:
        """Start the periodic flush loop."""
        self._stop_event.clear()
        self._flush_task = asyncio.create_task(self._flush_loop(), name="ticker-flush")

    async def stop(self) -> None:
        """Stop the flush loop and flush remaining buffer."""
        self._stop_event.set()
        if self._flush_task:
            try:
                await asyncio.wait_for(self._flush_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._flush_task.cancel()
        await self.flush()

    async def _flush_loop(self) -> None:
        """Flush every REDIS_FLUSH_MS."""
        interval = REDIS_FLUSH_MS / 1000.0
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break  # stop event set
            except asyncio.TimeoutError:
                pass
            try:
                await self.flush()
            except Exception as e:
                log.warning("[ticker-writer] flush error: %s", e)

    async def flush(self) -> None:
        """Flush buffered writes via a single Redis pipeline."""
        if not self._buffer:
            return

        # Snapshot and clear atomically
        items: List[Tuple[str, Dict[str, str]]] = list(self._buffer.items())
        self._buffer.clear()

        try:
            pipe = self._r.pipeline(transaction=False)
            for key, mapping in items:
                pipe.hset(key, mapping=mapping)
                pipe.expire(key, REDIS_KEY_TTL_S)
            await pipe.execute()
            self._flush_count += 1
            self._write_count += len(items)
            self._last_flush_at = time.time()
        except Exception as e:
            log.warning("[ticker-writer] pipeline failed (%d items): %s", len(items), e)
            # Re-buffer so we retry next cycle (avoid data loss)
            for key, mapping in items:
                self._buffer[key] = mapping

    @property
    def stats(self) -> dict:
        return {
            "flush_count": self._flush_count,
            "write_count": self._write_count,
            "buffer_size": len(self._buffer),
            "last_flush_age_s": (
                round(time.time() - self._last_flush_at, 3)
                if self._last_flush_at
                else None
            ),
        }