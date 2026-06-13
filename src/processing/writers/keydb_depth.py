"""
Redis Sentinel order-book depth writer for Flink stream processing.

Receives partial order-book depth snapshots and writes to Redis hashes.
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
WRITER_NAME = "keydb_depth"
SINK_NAME = "redis"
SOURCE_TOPIC = "crypto_depth"


class DepthWriter(FlatMapFunction):
    """Writes order-book snapshots to ``orderbook:{exchange}:{symbol}`` hashes in Redis Sentinel."""

    BATCH_SIZE = 50
    FLUSH_INTERVAL = 0.3

    def open(self, runtime_context):
        # Get Redis master connection via Sentinel
        self._r = get_flink_redis()
        self._buffer: list[dict] = []
        self._last_flush = time.time()
        self._known_keys: set[str] = set()
        init_metrics()

    def close(self):
        try:
            self._flush(trigger="close")
            self._r.close()
        except Exception as e:
            log.error("[Depth] close error: %s", e)

    def _flush(self, trigger: str = "time"):
        if not self._buffer:
            return
        n = len(self._buffer)
        record_buffer_size(WRITER_NAME, SINK_NAME, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            pipe = self._r.pipeline()
            for rec in self._buffer:
                symbol = rec["symbol"]
                exchange = rec["exchange"]
                bids = rec["bids"]
                asks = rec["asks"]

                # New key format: orderbook:{exchange}:{symbol}
                key = f"orderbook:{exchange}:{symbol}"
                pipe.hset(key, mapping={
                    "bids":           json.dumps(bids),
                    "asks":           json.dumps(asks),
                    "last_update_id": rec["last_update_id"],
                    "event_time":     rec["event_time"],
                    "exchange":       exchange,
                    "bid_depth":      len(bids),
                    "ask_depth":      len(asks),
                    "best_bid":       float(bids[0][0]) if bids else 0,
                    "best_ask":       float(asks[0][0]) if asks else 0,
                    "spread":         round(float(asks[0][0]) - float(bids[0][0]), 8) if bids and asks else 0,
                })
                pipe.expire(key, 300)
            pipe.execute()
        except Exception as e:
            error_type = type(e).__name__
            log.error("[Depth] flush error (dropped %d records): %s",
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
                "symbol":         symbol,
                "exchange":       exchange,
                "bids":           value.get("bids", []),
                "asks":           value.get("asks", []),
                "last_update_id": int(value.get("last_update_id", 0)),
                "event_time":     event_time,
            })
            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=event_time / 1000.0,
            )

            exchange_key = exchange
            if exchange_key not in self._known_keys:
                self._known_keys.add(exchange_key)
                record_writer_new_key(writer=WRITER_NAME, exchange=exchange)

            record_buffer_size(WRITER_NAME, SINK_NAME, len(self._buffer))

            if (
                len(self._buffer) >= self.BATCH_SIZE
                or (time.time() - self._last_flush) >= self.FLUSH_INTERVAL
            ):
                self._flush(trigger="size" if len(self._buffer) >= self.BATCH_SIZE else "time")
        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[Depth] flat_map error | symbol=%s error=%s", s, e)
            record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
        return []
