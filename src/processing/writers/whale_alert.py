"""
Whale Alert Writer for Flink stream processing (Task 2, v0.24.4).

Consumes aggregate trade records from Kafka ``crypto_trades`` and
emits a "whale alert" record whenever a single trade's notional value
(``price × quantity``) exceeds a configurable threshold (default
$100,000 USD). Whale alerts are written to:

- **Redis Sentinel** sorted set ``whale:alerts:{exchange}:{symbol}`` with
  TTL 1h. Used by the API for fast ``GET /api/market/whale-alerts`` reads
  and for WebSocket fan-out.
- **InfluxDB** measurement ``whale_alerts`` for historical analysis
  and trend dashboards.

This writer is intentionally separate from ``KeyDBTradeWriter`` so the
filter logic doesn't slow down the hot trade-aggregation path. Trades
that do not meet the threshold are silently dropped here (not buffered,
not persisted).

Filtering is intentionally simple (no state, no CEP). The complexity
worth caring about is:
- Buyer-maker flag → trade side (buy/sell)
- Price × quantity arithmetic in USD (the trade is already in quote
  asset = USDT, so we treat USDT ≈ USD for the threshold check)
- Dedup on the Redis sorted set to avoid double-counting
  replays from Kafka.
"""

import json
import logging
import os
import time

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
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
    record_whale_alert,
)

log = logging.getLogger(__name__)

# Writer identity for metrics labels
WRITER_NAME = "whale_alert"
SINK_NAME = "redis+influxdb"
SOURCE_TOPIC = "crypto_trades"

# Minimum USD value to be considered a "whale" trade.
# Default $100K is the standard threshold used by Whale Alert services
# (e.g. Whale Alert, CryptoQuant) — it surfaces institutional-grade
# activity without spamming retail noise.
DEFAULT_MIN_WHALE_USD = 100_000.0

# Redis key prefix
REDIS_KEY_PREFIX = "whale:alerts"

# Redis TTL — alerts are "fresh" for 1h. Older alerts are still queryable
# from InfluxDB (the historical store) but the API's hot path only
# looks in Redis.
REDIS_TTL_SEC = 3600

# Max alerts per symbol — keep newest N entries. 1000 is a balance
# between cardinality and "show last 1000 alerts" list UX.
MAX_ENTRIES_PER_SYMBOL = 1000

# InfluxDB
INFLUX_URL    = os.environ.get("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.environ.get("INFLUX_ORG",    "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")


class WhaleAlertWriter(FlatMapFunction):
    """Filter large trades and persist to Redis + InfluxDB.

    Threshold: ``notional_usd = price * quantity``. If notional_usd >=
    ``min_whale_usd`` (constructor arg, default ``DEFAULT_MIN_WHALE_USD``),
    the trade is treated as a whale alert.

    Trade side: derived from ``is_buyer_maker``.
    - ``is_buyer_maker = True``  → the buyer is the maker → the taker sold
      → trade is a **SELL** (someone sold to a passive buyer).
    - ``is_buyer_maker = False`` → the buyer is the taker → trade is a
      **BUY** (someone bought aggressively).

    Output format (Redis value, JSON):
    ::

        {
            "trade_id":   12345,            # agg_trade_id
            "symbol":     "BTCUSDT",
            "exchange":   "binance",
            "side":       "buy" | "sell",
            "price":      50000.0,
            "quantity":   2.5,
            "notional_usd": 125000.0,
            "trade_time": 1700000000000,     # ms epoch
            "detected_at": 1700000000123,    # ms epoch, server-detected time
        }
    """

    BATCH_SIZE = 50
    # Whale alerts are low-volume by design (only >$100K), so a
    # 1s flush interval is fine — won't be a hot path.
    FLUSH_INTERVAL = 1.0

    def __init__(self, min_whale_usd: float = DEFAULT_MIN_WHALE_USD,
                 batch_size: int = BATCH_SIZE,
                 flush_interval_sec: float = FLUSH_INTERVAL):
        self.min_whale_usd = float(min_whale_usd)
        self.batch_size = int(batch_size)
        self.flush_interval_sec = float(flush_interval_sec)

    def open(self, runtime_context):
        self._r = get_flink_redis()
        self._influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        self._influx_write = self._influx.write_api(write_options=SYNCHRONOUS)
        self._buffer: list[dict] = []        # Redis payloads (dict of fields)
        self._influx_buffer: list[Point] = []  # InfluxDB points
        self._last_flush = time.time()
        self._known_keys: set[str] = set()
        self._write_count: dict[str, int] = {}
        init_metrics()

    def close(self):
        try:
            self._flush(trigger="close")
            self._r.close()
            self._influx.close()
        except Exception as e:
            log.error("[WhaleAlert] close error: %s", e)

    def _flush(self, trigger: str = "time"):
        n = len(self._buffer)
        if n == 0 and not self._influx_buffer:
            return
        record_buffer_size(WRITER_NAME, SINK_NAME, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            # ── Redis batch (one ZADD per alert, but pipelined) ────────────
            if self._buffer:
                pipe = self._r.pipeline()
                for value in self._buffer:
                    key = f"{REDIS_KEY_PREFIX}:{value['exchange']}:{value['symbol']}"
                    score = value["trade_time"]
                    member = json.dumps(value)
                    # Dedup by score (trade_time) to handle Kafka replays
                    pipe.zremrangebyscore(key, score, score)
                    pipe.zadd(key, {member: score})
                    pipe.expire(key, REDIS_TTL_SEC)
                    # Enforce max-entries cap
                    count_key = f"{value['exchange']}:{value['symbol']}"
                    count = self._write_count.get(count_key, 0) + 1
                    self._write_count[count_key] = count
                    if count % 100 == 0:  # cleanup every 100 inserts
                        pipe.zremrangebyrank(key, 0, -MAX_ENTRIES_PER_SYMBOL - 1)
                pipe.execute()

            # ── InfluxDB batch ────────────────────────────────────────────
            if self._influx_buffer:
                self._influx_write.write(
                    bucket=INFLUX_BUCKET, org=INFLUX_ORG,
                    record=self._influx_buffer,
                )
        except Exception as e:
            error_type = type(e).__name__
            log.error("[WhaleAlert] flush error (dropped %d records): %s",
                      n, e)
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
            self._influx_buffer.clear()
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

            price = float(value.get("price", 0))
            quantity = float(value.get("quantity", 0))
            notional_usd = price * quantity

            if notional_usd < self.min_whale_usd:
                # Not a whale — drop silently. The KeyDB trade writer
                # still captures every trade; this is just the
                # pre-filter for alerting.
                record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
                return []

            exchange = value.get("exchange", "binance")
            trade_time = int(value.get("trade_time", 0))
            is_buyer_maker = bool(value.get("is_buyer_maker", False))
            side = "sell" if is_buyer_maker else "buy"

            alert = {
                "trade_id":     int(value.get("agg_trade_id", 0)),
                "symbol":       symbol,
                "exchange":     exchange,
                "side":         side,
                "price":        price,
                "quantity":     quantity,
                "notional_usd": notional_usd,
                "trade_time":   trade_time,
                "detected_at":  int(time.time() * 1000),
            }
            self._buffer.append(alert)

            point = (
                Point("whale_alerts")
                .tag("symbol",   symbol)
                .tag("exchange", exchange)
                .tag("side",     side)
                .field("price",         price)
                .field("quantity",      quantity)
                .field("notional_usd",  notional_usd)
                .field("trade_id",      alert["trade_id"])
                .time(trade_time, WritePrecision.MS)
            )
            self._influx_buffer.append(point)

            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=trade_time / 1000.0,
            )
            record_whale_alert(
                exchange=exchange, symbol=symbol, side=side,
                notional_usd=notional_usd,
            )

            exchange_key = exchange
            if exchange_key not in self._known_keys:
                self._known_keys.add(exchange_key)
                record_writer_new_key(writer=WRITER_NAME, exchange=exchange)

            record_buffer_size(WRITER_NAME, SINK_NAME, len(self._buffer))

            if (
                len(self._buffer) >= self.batch_size
                or (time.time() - self._last_flush) >= self.flush_interval_sec
            ):
                self._flush(
                    trigger="size" if len(self._buffer) >= self.batch_size else "time"
                )
        except Exception as e:
            s = value.get("symbol", "unknown") if isinstance(value, dict) else "unknown"
            log.error("[WhaleAlert] flat_map error | symbol=%s error=%s", s, e)
            record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
        return []
