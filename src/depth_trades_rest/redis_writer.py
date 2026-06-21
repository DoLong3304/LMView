"""Redis writer for binance-depth-trades-rest.

Two writers, one per stream:

- :class:`DepthWriter` writes the order book snapshot to a hash
  ``orderbook:binance:{symbol}`` with fields ``bids`` / ``asks`` (JSON),
  ``best_bid`` / ``best_ask`` / ``spread`` / ``event_time`` and a TTL.

- :class:`TradesWriter` appends aggregate trades to a sorted set
  ``trade:latest:binance:{symbol}``, scored by trade time in ms. Older
  entries past ``TRADES_HISTORY_MAX`` are trimmed.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Iterable, List, Sequence, Tuple

import redis.asyncio as redis_async

from src.depth_trades_rest.config import (
    DEPTH_TTL_S,
    TRADES_HISTORY_MAX,
    TRADES_TTL_S,
)

log = logging.getLogger("depth_trades_rest.redis_writer")


class DepthWriter:
    """Buffer + flush order book snapshots to Redis hashes."""

    def __init__(self, redis_client: redis_async.Redis, flush_ms: int = 500) -> None:
        self._redis = redis_client
        self._flush_ms = flush_ms
        self._buffer: dict[str, dict] = {}
        self._last_flush = time.monotonic()

    def enqueue(self, symbol: str, snapshot: dict) -> None:
        self._buffer[symbol] = snapshot

    async def flush(self, force: bool = False) -> int:
        if not self._buffer:
            return 0
        if not force and (time.monotonic() - self._last_flush) < (self._flush_ms / 1000.0):
            return 0

        n = len(self._buffer)
        # Pipeline is the only way to issue a HSET+EXPIRE round-trip per symbol
        # without paying N×RTT.
        try:
            pipe = self._redis.pipeline(transaction=False)
            for symbol, snap in self._buffer.items():
                key = f"orderbook:binance:{symbol}"
                mapping = {
                    "bids": json.dumps(snap["bids"]),
                    "asks": json.dumps(snap["asks"]),
                    "spread": str(snap["spread"]),
                    "best_bid": str(snap["best_bid"]),
                    "best_ask": str(snap["best_ask"]),
                    "event_time": str(snap["event_time"]),
                }
                pipe.hset(key, mapping=mapping)
                pipe.expire(key, DEPTH_TTL_S)
            await pipe.execute()
        except Exception as exc:
            log.error("[DepthWriter] flush failed: %s", exc)
            return 0
        finally:
            self._buffer.clear()
            self._last_flush = time.monotonic()
        return n


class TradesWriter:
    """Buffer + flush aggregate trades to Redis sorted sets."""

    def __init__(self, redis_client: redis_async.Redis, flush_ms: int = 250) -> None:
        self._redis = redis_client
        self._flush_ms = flush_ms
        self._buffer: dict[str, List[Tuple[int, str]]] = {}
        self._last_flush = time.monotonic()

    def enqueue(self, symbol: str, trades: Sequence[dict]) -> None:
        rows: List[Tuple[int, str]] = []
        for t in trades:
            score = int(t.get("T", 0))
            member = json.dumps(
                {
                    "t": score,
                    "p": t.get("p", "0"),
                    "q": t.get("q", "0"),
                    "m": bool(t.get("m", False)),
                },
                separators=(",", ":"),
            )
            rows.append((score, member))
        if rows:
            self._buffer.setdefault(symbol, []).extend(rows)

    async def flush(self, force: bool = False) -> int:
        if not self._buffer:
            return 0
        if not force and (time.monotonic() - self._last_flush) < (self._flush_ms / 1000.0):
            return 0

        total = 0
        try:
            pipe = self._redis.pipeline(transaction=False)
            for symbol, rows in self._buffer.items():
                key = f"trade:latest:binance:{symbol}"
                # ZADD with score=trade_time_ms. ZADD with same member+score is
                # idempotent (no duplicates) so re-running is safe.
                mapping = {member: score for score, member in rows}
                if mapping:
                    pipe.zadd(key, mapping)
                    # Keep only the most recent N entries to bound memory.
                    # ZREMRANGEBYRANK with negative indices removes the lowest
                    # scores (oldest), keeping the highest.
                    pipe.zremrangebyrank(key, 0, -(TRADES_HISTORY_MAX + 1))
                    pipe.expire(key, TRADES_TTL_S)
                    total += len(mapping)
            await pipe.execute()
        except Exception as exc:
            log.error("[TradesWriter] flush failed: %s", exc)
            return 0
        finally:
            self._buffer.clear()
            self._last_flush = time.monotonic()
        return total
