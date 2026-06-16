"""
Redis Sentinel ticker writer for Flink stream processing.

Batch-buffered: accumulates ticker updates and flushes via
a single Redis pipeline to minimize round trips.
"""

import json
import logging
import time

from pyflink.datastream.functions import FlatMapFunction
from common.flink_redis_sentinel import get_flink_redis
from writers.metrics import (
    record_flush,
    record_buffer_size,
    init_metrics,
    record_kafka_source,
    record_kafka_source_drop,
    record_kafka_source_deserialize,
    record_writer_event_time,
    record_writer_new_key,
)

log = logging.getLogger(__name__)

# Writer identity for metrics labels
WRITER_NAME = "keydb_ticker"
SINK_NAME = "redis"
SOURCE_TOPIC = "crypto_ticker"


class KeyDBWriter(FlatMapFunction):
    """Batch-buffered ticker writer to Redis Sentinel."""

    BATCH_SIZE = 100
    # B5 fix: reduced flush interval from 500ms to 200ms. With ~200
    # symbols the per-write cost is still <1ms in KeyDB, so the extra
    # flushes are cheap. This cuts the worst-case WebSocket cycle
    # latency in half while still amortising the TCP round-trip.
    FLUSH_INTERVAL = 0.2
    CLEANUP_EVERY = 60
    TICKER_HISTORY_TTL_SEC = 600

    def open(self, runtime_context):
        # Get Redis master connection via Sentinel
        self._r = get_flink_redis()
        self._buffer: list[dict] = []
        self._last_flush = time.time()
        self._write_count: dict[str, int] = {}
        # Track distinct keys we've already counted to avoid double-counting
        # per-restart (B7 warmup cost visibility)
        self._known_keys: set[str] = set()
        # Seed writer gauges so dashboards show 0 instead of "no data"
        # on the very first scrape after restart.
        init_metrics()

    def close(self):
        try:
            self._flush(trigger="close")
            self._r.close()
        except Exception as e:
            log.error("[KeyDB] close error: %s", e)

    def _flush(self, trigger: str = "time"):
        if not self._buffer:
            return
        n = len(self._buffer)
        # Update buffer-size gauge (now 0 because we're about to flush)
        record_buffer_size(WRITER_NAME, SINK_NAME, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            pipe = self._r.pipeline()
            for value in self._buffer:
                symbol = value["symbol"]
                exchange = value["exchange"]
                event_time = value["event_time"]
                price = value["price"]
                volume = value["volume"]

                # New key format: ticker:latest:{exchange}:{symbol}
                key = f"ticker:latest:{exchange}:{symbol}"
                pipe.hset(
                    key,
                    mapping={
                        "price":      price,
                        "bid":        value["bid"],
                        "ask":        value["ask"],
                        "volume":     volume,
                        "change24h":  value["change24h"],
                        "event_time": event_time,
                        "exchange":   exchange,
                    },
                )

                # History key also includes exchange
                history_key = f"ticker:history:{exchange}:{symbol}"
                pipe.zadd(history_key, {f"{price}:{volume}": event_time})
                pipe.expire(history_key, self.TICKER_HISTORY_TTL_SEC)

                count_key = f"{exchange}:{symbol}"
                count = self._write_count.get(count_key, 0) + 1
                self._write_count[count_key] = count
                if count % self.CLEANUP_EVERY == 0:
                    cutoff = event_time - 300_000
                    pipe.zremrangebyscore(history_key, 0, cutoff)
            pipe.execute()
        except Exception as e:
            error_type = type(e).__name__
            log.error("[KeyDB] flush error (dropped %d records): %s",
                      len(self._buffer), e)
        finally:
            duration = time.monotonic() - start
            record_flush(
                writer=WRITER_NAME,
                sink=SINK_NAME,
                duration_sec=duration,
                n_records=n,
                trigger=trigger,
                error=error_type,
            )
            self._buffer.clear()
            self._last_flush = time.time()

    def flat_map(self, value):
        try:
            if isinstance(value, (str, bytes)):
                deserialize_start = time.monotonic()
                value = json.loads(value)
                record_kafka_source_deserialize(
                    topic=SOURCE_TOPIC, duration_sec=time.monotonic() - deserialize_start
                )
            symbol = value.get("symbol")
            if not symbol:
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason="missing_symbol")
                return []
            exchange = value.get("exchange", "binance")
            event_time = int(value.get("event_time", 0))

            self._buffer.append({
                "symbol":     symbol,
                "exchange":   exchange,
                "event_time": event_time,
                "price":      float(value.get("close", 0)),
                "bid":        float(value.get("bid", 0)),
                "ask":        float(value.get("ask", 0)),
                "volume":     float(value.get("h24_volume", 0)),
                "change24h":  float(value.get("h24_price_change_pct", 0)),
            })
            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol, event_ts=event_time / 1000.0
            )

            # Per-key count (first time we see this exchange)
            exchange_key = exchange
            if exchange_key not in self._known_keys:
                self._known_keys.add(exchange_key)
                record_writer_new_key(writer=WRITER_NAME, exchange=exchange)

            # Update buffer size gauge after append
            record_buffer_size(WRITER_NAME, SINK_NAME, len(self._buffer))

            if (
                len(self._buffer) >= self.BATCH_SIZE
                or (time.time() - self._last_flush) >= self.FLUSH_INTERVAL
            ):
                self._flush(trigger="size" if len(self._buffer) >= self.BATCH_SIZE else "time")
        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[KeyDB] flat_map error | symbol=%s error=%s", s, e)
            record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
        return []
