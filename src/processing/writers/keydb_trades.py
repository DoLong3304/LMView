"""Redis Sentinel trade writer for Flink stream processing.

Writes aggregate trade records from Kafka crypto_trades to Redis sorted set.
Batch-buffered to reduce Redis round trips.
"""

import json
import logging
import time

from pyflink.datastream.functions import FlatMapFunction
from common.flink_redis_sentinel import get_flink_redis

log = logging.getLogger(__name__)

class KeyDBTradeWriter(FlatMapFunction):
    """Batch-buffered trade writer to Redis Sentinel.

    Key format: ``trade:latest:{exchange}:{symbol}`` (sorted set)
    Score = trade_time (ms), Member = trade JSON
    TTL = 600s per key.
    """

    BATCH_SIZE = 100
    FLUSH_INTERVAL = 0.5
    TRADE_TTL_SEC = 600
    MAX_ENTRIES = 200  # max trades per symbol

    def open(self, runtime_context):
        self._r = get_flink_redis()
        self._buffer: list[dict] = []
        self._last_flush = time.time()
        self._write_count: dict[str, int] = {}

    def close(self):
        try:
            self._flush()
            self._r.close()
        except Exception as e:
            log.error("[KeyDB/trades] close error: %s", e)

    def _flush(self):
        if not self._buffer:
            return
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
            log.error("[KeyDB/trades] flush error (dropped %d records): %s",
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

            trade_json = json.dumps({
                "p": float(value["price"]),
                "q": float(value["quantity"]),
                "t": int(value["trade_time"]),
                "m": bool(value.get("is_buyer_maker", False)),
                "T": int(value.get("event_time", 0)),
            })

            self._buffer.append({
                "symbol":     symbol,
                "exchange":   value.get("exchange", "binance"),
                "trade_time": int(value.get("trade_time", 0)),
                "trade_json": trade_json,
            })
            if (
                len(self._buffer) >= self.BATCH_SIZE
                or (time.time() - self._last_flush) >= self.FLUSH_INTERVAL
            ):
                self._flush()
        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[KeyDB/trades] flat_map error | symbol=%s error=%s", s, e)
        return []
