"""Single Binance WS shard = 1 connection = 1 asyncio task.

Handles WS lifecycle, frame parsing, exponential-backoff reconnect with
jitter, and writes parsed tickers to the shared ``TickerRedisWriter``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import TYPE_CHECKING

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidStatusCode,
    WebSocketException,
)

from src.ticker_ws.config import (
    PING_INTERVAL_S,
    PING_TIMEOUT_S,
    RECONNECT_BASE_MS,
    RECONNECT_MAX_MS,
)
from src.ticker_ws.parser import parse_ticker, redis_key

if TYPE_CHECKING:
    from src.ticker_ws.redis_writer import TickerRedisWriter

log = logging.getLogger(__name__)


class TickerShard:
    """One Binance WS combined-stream connection."""

    def __init__(
        self,
        shard_id: int,
        url: str,
        writer: "TickerRedisWriter",
    ):
        self.shard_id = shard_id
        self.url = url
        self.writer = writer

        # Stats
        self.frames_total = 0
        self.tickers_total = 0
        self.reconnects_total = 0
        self.last_frame_at: float = 0.0
        self.last_event_time_ms: int = 0
        self.connected = False
        self.connect_started_at: float = 0.0

    async def run(self, stop_event: asyncio.Event) -> None:
        """Run forever, reconnect on failure, until stop_event is set."""
        backoff_ms = RECONNECT_BASE_MS
        while not stop_event.is_set():
            try:
                await self._connect_and_consume(stop_event)
                backoff_ms = RECONNECT_BASE_MS  # success → reset
            except asyncio.CancelledError:
                raise
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
                log.warning(
                    "[shard %d] WS closed: %s (code=%s)",
                    self.shard_id, e, getattr(e, "code", "?"),
                )
                self.connected = False
            except InvalidStatusCode as e:
                log.warning(
                    "[shard %d] handshake failed: %s", self.shard_id, e,
                )
                self.connected = False
                if "403" in str(e) or "429" in str(e):
                    # Rate limit: longer backoff
                    backoff_ms = min(RECONNECT_MAX_MS, backoff_ms * 4)
            except (WebSocketException, OSError, asyncio.TimeoutError) as e:
                log.warning("[shard %d] connection error: %s", self.shard_id, e)
                self.connected = False
            except Exception as e:
                log.exception("[shard %d] unexpected: %s", self.shard_id, e)
                self.connected = False

            if stop_event.is_set():
                break

            # Exponential backoff with jitter
            jitter_ms = random.randint(0, 1000)
            sleep_ms = min(RECONNECT_MAX_MS, backoff_ms) + jitter_ms
            log.info(
                "[shard %d] reconnecting in %dms (attempt=%d)",
                self.shard_id, sleep_ms, self.reconnects_total + 1,
            )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_ms / 1000.0)
                break
            except asyncio.TimeoutError:
                pass
            backoff_ms = min(RECONNECT_MAX_MS, backoff_ms * 2)
            self.reconnects_total += 1

    async def _connect_and_consume(self, stop_event: asyncio.Event) -> None:
        """Open WS, consume frames until disconnect."""
        self.connect_started_at = time.time()
        log.info("[shard %d] connecting to %s", self.shard_id, self.url[:120] + "...")
        async with websockets.connect(
            self.url,
            ping_interval=PING_INTERVAL_S,
            ping_timeout=PING_TIMEOUT_S,
            close_timeout=5,
            max_size=8 * 1024 * 1024,
            open_timeout=15,
        ) as ws:
            self.connected = True
            log.info("[shard %d] connected", self.shard_id)
            while not stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(
                        ws.recv(), timeout=PING_INTERVAL_S + PING_TIMEOUT_S + 5,
                    )
                except asyncio.TimeoutError:
                    log.warning("[shard %d] recv timeout, closing", self.shard_id)
                    break
                self._handle_frame(raw)

    def _handle_frame(self, raw: str | bytes) -> None:
        """Parse one WS frame, write to Redis buffer."""
        self.frames_total += 1
        self.last_frame_at = time.time()
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                return

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        # Combined stream format: {"stream":"...","data":{...}}
        data = msg.get("data") if isinstance(msg, dict) else None
        if not isinstance(data, dict):
            return

        mapping = parse_ticker(data)
        if not mapping:
            return

        sym = data.get("s")
        if not sym:
            return

        key = redis_key("binance", sym)
        self.writer.add(key, mapping)
        self.tickers_total += 1
        try:
            self.last_event_time_ms = int(data.get("E", 0))
        except (ValueError, TypeError):
            pass

    @property
    def stats(self) -> dict:
        now = time.time()
        latency_ms = (
            now * 1000 - self.last_event_time_ms
            if self.last_event_time_ms
            else None
        )
        return {
            "shard_id": self.shard_id,
            "connected": self.connected,
            "frames_total": self.frames_total,
            "tickers_total": self.tickers_total,
            "reconnects_total": self.reconnects_total,
            "uptime_s": (
                round(now - self.connect_started_at, 1)
                if self.connected
                else 0
            ),
            "last_frame_age_s": (
                round(now - self.last_frame_at, 3) if self.last_frame_at else None
            ),
            "last_event_latency_ms": (
                round(latency_ms, 1) if latency_ms is not None else None
            ),
        }