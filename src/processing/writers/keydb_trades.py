"""
Redis Sentinel trade writer for Flink stream processing.

Writes aggregate trade records from Kafka crypto_trades to Redis sorted set.
Batch-buffered to reduce Redis round trips.
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
WRITER_NAME = "keydb_trade"
SINK_NAME = "redis"
SOURCE_TOPIC = "crypto_trades"

class KeyDBTradeWriter(FlatMapFunction):
    """Batch-buffered trade writer to Redis Sentinel.

    Key format: ``trade:latest:{exchange}:{symbol}`` (sorted set)
    Score = trade_time (ms), Member = trade JSON
    TTL = 600s per key.
    """

    BATCH_SIZE = 100
    # B5 fix: trades are the highest-priority stream (used by chart and
    # market overview), so we drop the flush interval from 500ms to
    # 200ms. Trade bursts (e.g. liquidation cascades) are still batched
    # via BATCH_SIZE so the network call count stays low.
    FLUSH_INTERVAL = 0.2
    TRADE_TTL_SEC = 3600  # 1 hour — sufficient for historical trade queries
    MAX_ENTRIES = 200  # max trades per symbol

    def open(self, runtime_context):
        self._r = get_flink_redis()
        self._buffer: list[dict] = []
        self._last_flush = time.time()
        self._write_count: dict[str, int] = {}
        self._known_keys: set[str] = set()
        init_metrics()

    def close(self):
        try:
            self._flush(trigger="close")
            self._r.close()
        except Exception as e:
            log.error("[KeyDB/trades] close error: %s", e)

    def _flush(self, trigger: str = "time"):
        if not self._buffer:
            return
        n = len(self._buffer)
        record_buffer_size(WRITER_NAME, SINK_NAME, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            pipe = self._r.pipeline()
            for value in self._buffer:
                symbol = value["symbol"]
                exchange = value["exchange"]
                trade_time = value["trade_time"]
                trade_json = value["trade_json"]

                key = f"trade:latest:{exchange}:{symbol}"
                # Dedup: remove existing entry for this trade_time
                pipe.zremrangebyscore(key, trade_time, trade_time)
                pipe.zadd(key, {trade_json: trade_time})
                pipe.expire(key, self.TRADE_TTL_SEC)

                # Enforce max entries: keep newest MAX_ENTRIES
                count_key = f"{exchange}:{symbol}"
                count = self._write_count.get(count_key, 0) + 1
                self._write_count[count_key] = count
                if count % self.MAX_ENTRIES == 0:
                    pipe.zremrangebyrank(key, 0, -self.MAX_ENTRIES - 1)

            pipe.execute()
        except Exception as e:
            error_type = type(e).__name__
            log.error("[KeyDB/trades] flush error (dropped %d records): %s",
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

            trade_json = json.dumps({
                "p": float(value["price"]),
                "q": float(value["quantity"]),
                "t": int(value["trade_time"]),
                "m": bool(value.get("is_buyer_maker", False)),
                "T": int(value.get("event_time", 0)),
            })

            exchange = value.get("exchange", "binance")
            trade_time = int(value.get("trade_time", 0))

            self._buffer.append({
                "symbol":     symbol,
                "exchange":   exchange,
                "trade_time": trade_time,
                "trade_json": trade_json,
            })
            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=trade_time / 1000.0,
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
            log.error("[KeyDB/trades] flat_map error | symbol=%s error=%s", s, e)
            record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
        return iter([])
