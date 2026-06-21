"""Binance REST kline poller with rate-limit + retry handling.

One ``KlinePoller`` instance owns the shared ``aiohttp.ClientSession`` and
runs concurrent sweeps over the symbol list. Each sweep fetches ``LIMIT``
candles per symbol, converts them to ``KlineUpdate`` objects, and feeds
them to the shared ``KlineRedisWriter``.

Concurrency is bounded by an ``asyncio.Semaphore`` (``MAX_CONCURRENT``).
On HTTP 429 / 456 (rate limit) the poller backs off process-wide via a
shared ``RateLimiter`` so all concurrent tasks respect the cooldown.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import List, Optional

import aiohttp

from src.kline_rest.config import (
    ENABLE_1S,
    INTER_SYMBOL_DELAY_S,
    KLINES_URL,
    LIMIT_1M,
    LIMIT_1S,
    MAX_CONCURRENT,
    POLL_INTERVAL_1M_S,
    POLL_INTERVAL_1S_S,
    REQUEST_TIMEOUT_S,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_BASE_S,
)
from src.kline_rest.redis_writer import KlineRedisWriter, KlineUpdate

log = logging.getLogger(__name__)

# Lazy import to keep the poller unit-testable without a Kafka cluster.
_avro_serializer = None


def _publish_to_kafka(symbol: str, interval: str, row: list, is_closed: bool) -> None:
    """Best-effort publish of one closed kline to the Kafka crypto_klines topic.

    The Spark lakehouse pipeline (``src/lakehouse/pipeline.py``) consumes
    this topic and writes closed candles to ``iceberg.crypto_lakehouse.coin_klines``.
    The binance-kline-rest poller is the sole producer now that the
    producer's @kline WebSocket stream is geofenced from AWS us-east-1.

    This runs synchronously in the poller thread pool; failures are
    logged and dropped (the candle is already in Redis so the next sweep
    will retry via the producer's idempotent ZADD with same score).
    """
    global _avro_serializer
    if not is_closed:
        # Spark only stores closed candles (its filter is `is_closed == True`),
        # so skip the still-forming one.
        return
    if _avro_serializer is None:
        return
    try:
        (open_time, o, h, l, c, v, qv, n) = _parse_kline_row(row, False)
    except Exception as exc:
        log.debug("[kafka] skip malformed row for %s/%s: %s", symbol, interval, exc)
        return
    import time as _time
    record = {
        "event_time":   int(_time.time() * 1000),
        "symbol":       symbol,
        "exchange":     "binance",
        "kline_start":  int(open_time),
        "kline_close":  int(open_time + _interval_to_ms(interval)),
        "interval":     interval,
        "open":         float(o),
        "high":         float(h),
        "low":          float(l),
        "close":        float(c),
        "volume":       float(v),
        "quote_volume": float(qv),
        "trade_count":  int(n),
        "is_closed":    True,
    }
    topic = os.environ.get("KAFKA_TOPIC_KLINES", "crypto_klines")
    try:
        from src.common.kafka_client import send_to_kafka
        send_to_kafka(topic, record, _avro_serializer)
    except Exception as exc:
        log.warning("[kafka] publish failed for %s/%s: %s", symbol, interval, exc)


def set_avro_serializer(serializer) -> None:
    """Inject the Avro serializer once the schema is registered."""
    global _avro_serializer
    _avro_serializer = serializer


def _interval_to_ms(interval: str) -> int:
    """Binance interval code to milliseconds."""
    n = int(interval[:-1])
    unit = interval[-1]
    if unit == "m":
        return n * 60_000
    if unit == "h":
        return n * 3_600_000
    if unit == "d":
        return n * 86_400_000
    if unit == "w":
        return n * 604_800_000
    if unit == "s":
        return n * 1_000
    return 60_000


class RateLimiter:
    """Process-wide gate that pauses all callers when Binance rate-limits us.

    When ``pause_until`` is set, every ``await gate()`` blocks until that
    timestamp. ``trigger(seconds)`` extends the pause if a 429/418 is seen.
    """

    def __init__(self) -> None:
        self._pause_until: float = 0.0
        self._cv = asyncio.Condition()

    async def gate(self) -> None:
        """Block while a rate-limit pause is active."""
        while True:
            async with self._cv:
                now = time.time()
                wait = self._pause_until - now
                if wait <= 0:
                    return
                try:
                    await asyncio.wait_for(self._cv.wait(), timeout=wait)
                except asyncio.TimeoutError:
                    continue

    async def trigger(self, seconds: float) -> None:
        """Declare a rate-limit pause of ``seconds`` (extends if longer)."""
        async with self._cv:
            new_until = time.time() + seconds
            if new_until > self._pause_until:
                self._pause_until = new_until
                log.warning(
                    "[rate-limiter] pausing all REST calls for %.1fs", seconds,
                )
            self._cv.notify_all()


def _parse_kline_row(row: list, is_last: bool) -> tuple[int, float, float, float, float, float, float, int]:
    """Extract canonical fields from one Binance kline row.

    Row layout:
        [openTime, open, high, low, close, volume, closeTime,
         quoteAssetVolume, numberOfTrades, takerBuyBaseVol,
         takerBuyQuoteVol, ignore]
    """
    return (
        int(row[0]),
        float(row[1]),
        float(row[2]),
        float(row[3]),
        float(row[4]),
        float(row[5]),
        float(row[7]),
        int(row[8]),
    )


class KlinePoller:
    """Polls Binance REST klines for a symbol list, feeds Redis writer."""

    def __init__(
        self,
        writer: KlineRedisWriter,
        rate_limiter: RateLimiter,
        symbols: List[str],
    ) -> None:
        self._writer = writer
        self._rate_limiter = rate_limiter
        self._symbols = symbols
        self._sem = asyncio.Semaphore(MAX_CONCURRENT)
        self._session: aiohttp.ClientSession | None = None

        # Stats (per-interval)
        self.sweeps_1m = 0
        self.sweeps_1s = 0
        self.candles_1m = 0
        self.candles_1s = 0
        self.errors = 0
        self.rate_limited = 0
        self.last_sweep_1m_at: float = 0.0
        self.last_sweep_1s_at: float = 0.0
        self.last_error: str | None = None

    async def __aenter__(self) -> "KlinePoller":
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_S)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _fetch_klines(
        self, symbol: str, interval: str, limit: int,
    ) -> list[list] | None:
        """Fetch klines for one symbol with retry + rate-limit handling.

        Returns ``None`` on persistent failure (caller logs + skips).
        """
        await self._rate_limiter.gate()
        params = {"symbol": symbol, "interval": interval, "limit": str(limit)}
        last_err: Exception | None = None

        for attempt in range(RETRY_ATTEMPTS):
            async with self._sem:
                try:
                    assert self._session is not None
                    async with self._session.get(KLINES_URL, params=params) as resp:
                        if resp.status == 429 or resp.status == 418:
                            # IP banned (418) or rate limited (429).
                            retry_after = int(resp.headers.get("Retry-After", "60"))
                            self.rate_limited += 1
                            await self._rate_limiter.trigger(float(retry_after))
                            # Retry after gate clears.
                            await self._rate_limiter.gate()
                            continue
                        if resp.status >= 500:
                            # Transient server error — short backoff + retry.
                            last_err = aiohttp.ClientResponseError(
                                resp.request_info, resp.history,
                                status=resp.status, message=resp.reason or "",
                            )
                            await asyncio.sleep(RETRY_BACKOFF_BASE_S * (2 ** attempt))
                            continue
                        resp.raise_for_status()
                        return await resp.json()
                except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                    last_err = e
                    await asyncio.sleep(RETRY_BACKOFF_BASE_S * (2 ** attempt))
                    continue

        self.errors += 1
        self.last_error = f"{symbol}/{interval}: {last_err}"
        log.warning("[poller] %s/%s failed after %d attempts: %s",
                    symbol, interval, RETRY_ATTEMPTS, last_err)
        return None

    def _enqueue_rows(
        self, symbol: str, interval: str, rows: list[list], update_latest: bool,
    ) -> int:
        """Convert REST rows → KlineUpdate buffer entries. Returns count."""
        if not rows:
            return 0
        last_idx = len(rows) - 1
        for i, row in enumerate(rows):
            try:
                (open_time, o, h, l, c, v, qv, n) = _parse_kline_row(row, i == last_idx)
            except (ValueError, IndexError, TypeError) as e:
                log.debug("[poller] %s/%s skip malformed row %d: %s", symbol, interval, i, e)
                continue
            # The last row in a Binance kline response is the still-forming
            # candle; mark it not-closed so the frontend treats it as live.
            is_closed = i != last_idx
            self._writer.add(KlineUpdate(
                symbol=symbol,
                interval=interval,
                open_time_ms=open_time,
                o=o, h=h, l=l, c=c, v=v, qv=qv, n=n,
                is_closed=is_closed,
                update_latest=update_latest,
            ))
            # Mirror closed candles to the Kafka topic that feeds the
            # Spark lakehouse. The Kafka publisher is best-effort;
            # ZADD in Redis is idempotent so the next sweep will retry
            # any candle that did not reach Kafka.
            if is_closed:
                _publish_to_kafka(symbol, interval, row, True)
        return len(rows)

    async def _sweep(self, interval: str, limit: int, update_latest: bool) -> int:
        """One pass over all symbols for a given interval. Returns candle count."""
        total = 0
        tasks: list[asyncio.Task] = []
        # Drive the sweep with bounded concurrency; stagger starts slightly
        # so we never fire the full symbol list as one burst.
        for sym in self._symbols:
            tasks.append(asyncio.create_task(self._poll_one(sym, interval, limit, update_latest)))
            if INTER_SYMBOL_DELAY_S:
                await asyncio.sleep(INTER_SYMBOL_DELAY_S)
        for t in asyncio.as_completed(tasks):
            n = await t
            total += n
        return total

    async def _poll_one(
        self, symbol: str, interval: str, limit: int, update_latest: bool,
    ) -> int:
        rows = await self._fetch_klines(symbol, interval, limit)
        if not rows:
            return 0
        return self._enqueue_rows(symbol, interval, rows, update_latest)

    async def run_1m_loop(self, stop_event: asyncio.Event) -> None:
        """Periodically poll 1m candles until stopped."""
        log.info("[poller] 1m loop started: %d symbols every %ds",
                 len(self._symbols), POLL_INTERVAL_1M_S)
        while not stop_event.is_set():
            t0 = time.time()
            try:
                count = await self._sweep("1m", LIMIT_1M, update_latest=True)
                self.candles_1m += count
                self.sweeps_1m += 1
                self.last_sweep_1m_at = time.time()
                log.info("[poller] 1m sweep #%d done: %d candles in %.2fs",
                         self.sweeps_1m, count, self.last_sweep_1m_at - t0)
            except Exception as e:
                self.errors += 1
                self.last_error = f"1m-sweep: {e}"
                log.exception("[poller] 1m sweep error: %s", e)
            # Sleep remaining interval (or 0 if sweep overran)
            elapsed = time.time() - t0
            sleep_for = max(0.0, POLL_INTERVAL_1M_S - elapsed)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                pass

    async def run_1s_loop(self, stop_event: asyncio.Event) -> None:
        """Periodically poll 1s candles until stopped. Only if ENABLE_1S."""
        if not ENABLE_1S:
            log.info("[poller] 1s loop disabled (KLINE_REST_ENABLE_1S != true)")
            return
        log.info("[poller] 1s loop started: %d symbols every %ds",
                 len(self._symbols), POLL_INTERVAL_1S_S)
        while not stop_event.is_set():
            t0 = time.time()
            try:
                count = await self._sweep("1s", LIMIT_1S, update_latest=False)
                self.candles_1s += count
                self.sweeps_1s += 1
                self.last_sweep_1s_at = time.time()
                log.debug("[poller] 1s sweep #%d: %d candles in %.2fs",
                          self.sweeps_1s, count, self.last_sweep_1s_at - t0)
            except Exception as e:
                self.errors += 1
                self.last_error = f"1s-sweep: {e}"
                log.exception("[poller] 1s sweep error: %s", e)
            elapsed = time.time() - t0
            sleep_for = max(0.0, POLL_INTERVAL_1S_S - elapsed)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                pass

    @property
    def stats(self) -> dict:
        return {
            "symbols": len(self._symbols),
            "sweeps_1m": self.sweeps_1m,
            "sweeps_1s": self.sweeps_1s,
            "candles_1m": self.candles_1m,
            "candles_1s": self.candles_1s,
            "errors": self.errors,
            "rate_limited": self.rate_limited,
            "last_sweep_1m_age_s": (
                round(time.time() - self.last_sweep_1m_at, 2)
                if self.last_sweep_1m_at else None
            ),
            "last_sweep_1s_age_s": (
                round(time.time() - self.last_sweep_1s_at, 2)
                if self.last_sweep_1s_at else None
            ),
            "last_error": self.last_error,
        }
