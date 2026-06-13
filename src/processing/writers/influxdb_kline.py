"""
InfluxDB kline candle writer for Flink stream processing.

Writes closed 1m candles to InfluxDB ``candles`` measurement for 90-day analytics.
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
WRITER_NAME = "influxdb_kline"
SINK_NAME = "influxdb"
SOURCE_TOPIC = "crypto_klines"


class InfluxDBKlineWriter(FlatMapFunction):
    """Writes closed 1m klines to InfluxDB ``candles`` measurement."""

    def __init__(self, batch_size: int = 500, flush_interval_sec: float = 3.0):
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
            log.error("[InfluxDB/candles] flush error (dropped %d points): %s", len(self._buffer), e)
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
            log.error("[InfluxDB/candles] close error: %s", e)

    def flat_map(self, value):
        try:
            if isinstance(value, (str, bytes)):
                deserialize_start = time.monotonic()
                value = json.loads(value)
                record_kafka_source_deserialize(
                    topic=SOURCE_TOPIC, duration_sec=time.monotonic() - deserialize_start
                )

            # InfluxDB stores only closed 1m candles for 90-day analytics/history.
            if value.get("interval") != "1m" or not bool(value.get("is_closed", False)):
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason="not_closed_1m")
                return []

            exchange = value.get("exchange", "binance")
            symbol = value.get("symbol")
            if not symbol:
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason="missing_symbol")
                return []

            point = (
                Point("candles")
                .tag("symbol",   symbol)
                .tag("exchange", exchange)
                .tag("interval", value.get("interval", "1m"))
                .field("open",         float(value["open"]))
                .field("high",         float(value["high"]))
                .field("low",          float(value["low"]))
                .field("close",        float(value["close"]))
                .field("volume",       float(value["volume"]))
                .field("quote_volume", float(value["quote_volume"]))
                .field("trade_count",  int(value["trade_count"]))
                .field("is_closed",    bool(value["is_closed"]))
                .time(int(value["kline_start"]), WritePrecision.MS)
            )
            self._buffer.append(point)
            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=int(value["kline_start"]) / 1000.0,
            )

            exchange_key = f"{exchange}:kline"
            if exchange_key not in self._known_keys:
                self._known_keys.add(exchange_key)
                record_writer_new_key(writer=WRITER_NAME, exchange=exchange_key)

            record_buffer_size(WRITER_NAME, SINK_NAME, len(self._buffer))

            if (
                len(self._buffer) >= self.batch_size
                or (time.time() - self._last_flush_time) >= self.flush_interval_sec
            ):
                self._flush(trigger="size" if len(self._buffer) >= self.batch_size else "time")
        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[InfluxDB/candles] flat_map error | symbol=%s error=%s", s, e)
            record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
        return []
