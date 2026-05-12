"""
Redis Sentinel ticker writer for Flink stream processing.

Batch-buffered: accumulates ticker updates and flushes via
a single Redis pipeline to minimize round trips.
"""

import json
import logging
import os
import time

from pyflink.datastream.functions import FlatMapFunction
from common.flink_redis_sentinel import get_flink_redis

log = logging.getLogger(__name__)


class KeyDBWriter(FlatMapFunction):
    """Batch-buffered ticker writer to Redis Sentinel."""

    BATCH_SIZE = 100
    FLUSH_INTERVAL = 0.5
    CLEANUP_EVERY = 60
    TICKER_HISTORY_TTL_SEC = 600

    def open(self, runtime_context):
        # Get Redis master connection via Sentinel
        self._r = get_flink_redis()
        self._buffer: list[dict] = []
        self._last_flush = time.time()
        self._write_count: dict[str, int] = {}

    def close(self):
        try:
            self._flush()
            self._r.close()
        except Exception as e:
            log.error("[KeyDB] close error: %s", e)

    def _flush(self):
        if not self._buffer:
            return
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
            log.error("[KeyDB] flush error (dropped %d records): %s",
                      len(self._buffer), e)
        finally:
            self._buffer.clear()
            self._last_flush = time.time()

    def flat_map(self, value):
        try:
            if isinstance(value, (str, bytes)):
                value = json.loads(value)
            symbol = value.get("symbol")
            if not symbol:
                return []
            self._buffer.append({
                "symbol":     symbol,
                "exchange":   value.get("exchange", "binance"),
                "event_time": int(value.get("event_time", 0)),
                "price":      float(value.get("close", 0)),
                "bid":        float(value.get("bid", 0)),
                "ask":        float(value.get("ask", 0)),
                "volume":     float(value.get("h24_volume", 0)),
                "change24h":  float(value.get("h24_price_change_pct", 0)),
            })
            if (
                len(self._buffer) >= self.BATCH_SIZE
                or (time.time() - self._last_flush) >= self.FLUSH_INTERVAL
            ):
                self._flush()
        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[KeyDB] flat_map error | symbol=%s error=%s", s, e)
        return []
