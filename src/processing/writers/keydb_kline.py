"""
Redis Sentinel kline candle writer for Flink stream processing.

Writes 1s and 1m candles to Redis sorted sets with interval-specific TTLs.
Batch-buffered to reduce Redis round trips.
"""

import json
import logging
import os
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

KEYDB_1S_RETENTION_DAYS = int(os.environ.get("KEYDB_1S_RETENTION_DAYS", "1"))
KEYDB_1M_RETENTION_DAYS = int(os.environ.get("KEYDB_1M_RETENTION_DAYS", "7"))

log = logging.getLogger(__name__)

# Writer identity for metrics labels
WRITER_NAME = "keydb_kline"
SINK_NAME = "redis"
SOURCE_TOPIC = "crypto_klines"


class KeyDBKlineWriter(FlatMapFunction):
    """Writes kline candles to Redis Sentinel with interval-specific TTL.

    - ``candle:1s:{exchange}:{symbol}`` → TTL KEYDB_1S_RETENTION_DAYS
    - ``candle:1m:{exchange}:{symbol}`` → TTL KEYDB_1M_RETENTION_DAYS
    - ``candle:latest:{exchange}:{symbol}`` → latest candle info (1m+ only)
    """

    TTL_1S = max(KEYDB_1S_RETENTION_DAYS, 1) * 86_400
    TTL_1M = max(KEYDB_1M_RETENTION_DAYS, 1) * 86_400
    CLEANUP_EVERY = 60
    BATCH_SIZE = 50
    FLUSH_INTERVAL = 0.1  # was 0.5 — reduced from 500ms to 100ms for lower latency

    def open(self, runtime_context):
        # Get Redis master connection via Sentinel
        self._r = get_flink_redis()
        self._write_count: dict[str, int] = {}
        self._buffer: list[dict] = []
        self._last_flush = time.time()
        # Track exchanges we've already counted as a new key
        self._known_keys: set[str] = set()
        init_metrics()

    def close(self):
        try:
            self._flush(trigger="close")
            self._r.close()
        except Exception as e:
            log.error("[KeyDB/candles] close error: %s", e)

    def _flush(self, trigger: str = "time"):
        if not self._buffer:
            return
        n = len(self._buffer)
        record_buffer_size(WRITER_NAME, SINK_NAME, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            pipe = self._r.pipeline()
            for item in self._buffer:
                symbol = item["symbol"]
                exchange = item["exchange"]
                interval = item["interval"]
                kline_start = item["kline_start"]
                candle_json = item["candle_json"]
                history_key = item["history_key"]
                ttl_sec = item["ttl_sec"]

                pipe.zremrangebyscore(history_key, kline_start, kline_start)
                pipe.zadd(history_key, {candle_json: kline_start})
                pipe.expire(history_key, ttl_sec)

                if interval != "1s":
                    latest_key = f"candle:latest:{exchange}:{symbol}"
                    pipe.hset(latest_key, mapping=item["latest_mapping"])

                count_key = f"{exchange}:{symbol}"
                count = self._write_count.get(count_key, 0) + 1
                self._write_count[count_key] = count
                if count % self.CLEANUP_EVERY == 0:
                    cutoff = kline_start - (ttl_sec * 1000)
                    pipe.zremrangebyscore(history_key, 0, cutoff)

            pipe.execute()
        except Exception as e:
            error_type = type(e).__name__
            log.error("[KeyDB/candles] flush error (dropped %d records): %s",
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
                return iter([])
            exchange = value.get("exchange", "binance")
            interval = value.get("interval", "1m")
            if interval not in ("1s", "1m"):
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason="unsupported_interval")
                return iter([])
            kline_start = int(value["kline_start"])

            candle_json = json.dumps({
                "t": kline_start,
                "o": float(value["open"]),
                "h": float(value["high"]),
                "l": float(value["low"]),
                "c": float(value["close"]),
                "v": float(value["volume"]),
                "qv": float(value["quote_volume"]),
                "n": int(value["trade_count"]),
                "x": bool(value["is_closed"]),
            })

            # New key format includes exchange
            if interval == "1s":
                history_key = f"candle:1s:{exchange}:{symbol}"
                ttl_sec = self.TTL_1S
            else:
                history_key = f"candle:1m:{exchange}:{symbol}"
                ttl_sec = self.TTL_1M

            self._buffer.append({
                "symbol": symbol,
                "exchange": exchange,
                "interval": interval,
                "kline_start": kline_start,
                "candle_json": candle_json,
                "history_key": history_key,
                "ttl_sec": ttl_sec,
                "latest_mapping": {
                    "open":         float(value["open"]),
                    "high":         float(value["high"]),
                    "low":          float(value["low"]),
                    "close":        float(value["close"]),
                    "volume":       float(value["volume"]),
                    "quote_volume": float(value["quote_volume"]),
                    "trade_count":  int(value["trade_count"]),
                    "is_closed":    int(value["is_closed"]),
                    "kline_start":  kline_start,
                    "interval":     interval,
                    "exchange":     exchange,
                },
            })

            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=kline_start / 1000.0,
            )

            exchange_key = f"{exchange}:{interval}"
            if exchange_key not in self._known_keys:
                self._known_keys.add(exchange_key)
                record_writer_new_key(writer=WRITER_NAME, exchange=exchange_key)

            record_buffer_size(WRITER_NAME, SINK_NAME, len(self._buffer))

            if (
                len(self._buffer) >= self.BATCH_SIZE
                or (time.time() - self._last_flush) >= self.FLUSH_INTERVAL
            ):
                self._flush(trigger="size" if len(self._buffer) >= self.BATCH_SIZE else "time")
        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[KeyDB/candles] flat_map error | symbol=%s error=%s", s, e)
            record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
        return iter([])
