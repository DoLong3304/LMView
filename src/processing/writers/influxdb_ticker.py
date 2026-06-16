"""
InfluxDB ticker writer for Flink stream processing.

Writes market tick data points to InfluxDB ``market_ticks`` measurement.
"""

import json
import logging
import os
import time

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pyflink.datastream.functions import FlatMapFunction
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

INFLUX_URL    = os.environ.get("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.environ.get("INFLUX_ORG",    "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

log = logging.getLogger(__name__)

# Writer identity for metrics labels
WRITER_NAME = "influxdb_ticker"
SINK_NAME = "influxdb"
SOURCE_TOPIC = "crypto_ticker"


class InfluxDBWriter(FlatMapFunction):
    """Batch-buffered ticker writer to InfluxDB ``market_ticks`` measurement."""

    def __init__(self, batch_size: int = 200, flush_interval_sec: float = 0.5):
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec

    def open(self, runtime_context):
        self._client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        self._buffer = []
        self._last_flush_time = time.time()
        self._known_keys: set[str] = set()
        init_metrics()

    def _flush(self, trigger: str = "time"):
        if not self._buffer:
            return
        n = len(self._buffer)
        record_buffer_size(WRITER_NAME, SINK_NAME, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=self._buffer)
        except Exception as e:
            error_type = type(e).__name__
            log.error("[InfluxDB] flush error (dropped %d points): %s", len(self._buffer), e)
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
            self._last_flush_time = time.time()

    def close(self):
        try:
            self._flush(trigger="close")
            self._client.close()
        except Exception as e:
            log.error("[InfluxDB] close error: %s", e)

    def flat_map(self, value):
        try:
            if isinstance(value, (str, bytes)):
                deserialize_start = time.monotonic()
                value = json.loads(value)
                record_kafka_source_deserialize(
                    topic=SOURCE_TOPIC, duration_sec=time.monotonic() - deserialize_start
                )

            exchange = value.get("exchange", "binance")
            symbol = value.get("symbol")
            if not symbol:
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason="missing_symbol")
                return []

            point = (
                Point("market_ticks")
                .tag("symbol",   symbol)
                .tag("exchange", exchange)
                .field("price",             float(value.get("close", 0)))
                .field("bid",               float(value.get("bid", 0)))
                .field("ask",               float(value.get("ask", 0)))
                .field("volume",            float(value.get("h24_volume", 0)))
                .field("quote_volume",      float(value.get("h24_quote_volume", 0)))
                .field("price_change_pct",  float(value.get("h24_price_change_pct", 0)))
                .field("trade_count",       int(value.get("h24_trade_count", 0)))
                .time(int(value["event_time"]), WritePrecision.MS)
            )
            self._buffer.append(point)
            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=int(value["event_time"]) / 1000.0,
            )

            exchange_key = exchange
            if exchange_key not in self._known_keys:
                self._known_keys.add(exchange_key)
                record_writer_new_key(writer=WRITER_NAME, exchange=exchange)

            record_buffer_size(WRITER_NAME, SINK_NAME, len(self._buffer))

            if (
                len(self._buffer) >= self.batch_size
                or (time.time() - self._last_flush_time) >= self.flush_interval_sec
            ):
                self._flush(trigger="size" if len(self._buffer) >= self.batch_size else "time")
        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[InfluxDB] flat_map error | symbol=%s error=%s", s, e)
            record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
        return []
