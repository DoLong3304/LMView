"""
Technical indicator writer for Flink stream processing.

Receives closed 1m klines, maintains rolling close-price buffers per symbol,
computes SMA20, SMA50, EMA12, EMA26, and writes results to Redis Sentinel + InfluxDB.
"""

import json
import logging
import os
import time
from collections import deque
from statistics import pstdev

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pyflink.datastream.functions import FlatMapFunction
from common.flink_redis_sentinel import get_flink_redis
from writers.metrics import (
    record_flush,
    record_buffer_size,
    record_indicator_warmup,
    record_indicator_recompute,
    init_metrics,
    record_kafka_source,
    record_kafka_source_drop,
    record_kafka_source_deserialize,
    record_writer_event_time,
    record_writer_new_key,
    INDICATOR_STATE_KEYS,
)

INFLUX_URL    = os.environ.get("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.environ.get("INFLUX_ORG",    "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

log = logging.getLogger(__name__)

# Writer identity for metrics labels
WRITER_NAME = "indicator"
SINK_NAME_REDIS = "redis"
SINK_NAME_INFLUX = "influxdb"
SOURCE_TOPIC = "crypto_klines_indicators"


class IndicatorWriter(FlatMapFunction):
    """Computes SMA/EMA indicators from closed 1m klines.

    Outputs:
        - ``indicator:latest:{exchange}:{symbol}`` hash in Redis Sentinel
        - ``indicators`` measurement in InfluxDB

    State retention note (B7):
        The EMA / MACD signal state lives in this in-process dict
        (``self._ema_state``). On Flink restart this state is
        re-warmed by replaying recent klines. The warmup duration
        is recorded via :func:`record_indicator_warmup` so that
        operators can see how long the post-restart hydration takes.
    """

    SMA_PERIODS = (20, 50)
    EMA_PERIODS = (12, 26)
    MAX_HISTORY = 60  # keep last 60 closes (enough for SMA50 + buffer)

    @staticmethod
    def _avg(values):
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def _sma(values, period):
        if len(values) < period:
            return None
        window = list(values)[-period:]
        return sum(window) / period

    @staticmethod
    def _rsi(values, period=14):
        if len(values) < period + 1:
            return None
        closes = list(values)
        gains = 0.0
        losses = 0.0
        for idx in range(-period, 0):
            diff = closes[idx] - closes[idx - 1]
            if diff > 0:
                gains += diff
            else:
                losses -= diff
        avg_gain = gains / period
        avg_loss = losses / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _bollinger(values, period=20, multiplier=2.0):
        if len(values) < period:
            return None, None, None, None
        window = list(values)[-period:]
        middle = sum(window) / period
        deviation = pstdev(window) * multiplier if period > 1 else 0.0
        upper = middle + deviation
        lower = middle - deviation
        width = upper - lower
        return middle, upper, lower, width

    @staticmethod
    def _atr(candles, period=14):
        rows = list(candles)
        if len(rows) < period + 1:
            return None
        true_ranges = []
        for idx in range(len(rows) - period, len(rows)):
            cur = rows[idx]
            prev = rows[idx - 1]
            tr = max(
                cur["high"] - cur["low"],
                abs(cur["high"] - prev["close"]),
                abs(cur["low"] - prev["close"]),
            )
            true_ranges.append(tr)
        return sum(true_ranges) / len(true_ranges) if true_ranges else None

    def open(self, runtime_context):
        # Get Redis master connection via Sentinel
        self._r = get_flink_redis()
        self._influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        self._write_api = self._influx_client.write_api(write_options=SYNCHRONOUS)
        self._closes: dict[str, deque] = {}
        self._volumes: dict[str, deque] = {}
        self._candles: dict[str, deque] = {}
        self._ema_state: dict[str, dict[int, float]] = {}
        self._macd_signal_state: dict[str, float] = {}
        self._buffer = []
        self._last_flush = time.time()
        self._history_ttl_sec = int(os.environ.get("INDICATOR_HISTORY_TTL_SEC", "604800"))
        self._history_max_entries = int(os.environ.get("INDICATOR_HISTORY_MAX_ENTRIES", "10080"))
        self._history_write_count: dict[str, int] = {}

        # B7 fix — wire the persistent state store so a Flink restart
        # can re-hydrate the in-process dicts from Redis without
        # needing a Kafka replay.
        from writers.indicator_state import IndicatorStateStore
        self._state_store = IndicatorStateStore(self._r)
        # Hydrate from Redis. We don't know the exchange here yet
        # (Flink assigns subtasks per-key later) so the first emit
        # will trigger a per-exchange hydrate.
        self._hydrated_exchanges: set[str] = set()

        # Track warmup timing (B7 visibility). _open_time is the moment
        # this subtask becomes ready to process; we mark warmup complete
        # once we've emitted indicators for the first new candle for
        # every previously-known key (or after the first minute of work).
        self._open_time = time.monotonic()
        self._first_candles_seen: set[str] = set()
        self._warmup_recorded = False
        init_metrics()

    def _record_state_keys(self) -> None:
        """Snapshot the in-memory state-key gauges.

        These gauges make the in-memory indicator dict (B7) visible
        to operators. We update the gauge lazily on each emit rather
        than maintaining a separate counter, so the value is always
        consistent with the current process state.
        """
        try:
            closes = len(self._closes)
            volumes = len(self._volumes)
            candles = len(self._candles)
            ema = len(self._ema_state)
            macd = len(self._macd_signal_state)
            # Use the closes count as the "active symbol" gauge and
            # expose the per-state breakdown as separate labels
            INDICATOR_STATE_KEYS.labels(state_type="candle_deque").set(candles)
            INDICATOR_STATE_KEYS.labels(state_type="closes_deque").set(closes)
            INDICATOR_STATE_KEYS.labels(state_type="volumes_deque").set(volumes)
            INDICATOR_STATE_KEYS.labels(state_type="ema_state").set(ema)
            INDICATOR_STATE_KEYS.labels(state_type="macd_signal").set(macd)
        except Exception as e:
            # Never let metric emission break the main pipeline
            log.debug("[Indicators] state-keys gauge update failed: %s", e)

    def _flush_influx(self, trigger: str = "time"):
        if not self._buffer:
            return
        n = len(self._buffer)
        record_buffer_size(WRITER_NAME, SINK_NAME_INFLUX, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=self._buffer)
        except Exception as e:
            error_type = type(e).__name__
            log.error("[Indicators/InfluxDB] flush error: %s", e)
        finally:
            duration = time.monotonic() - start
            record_flush(
                writer=WRITER_NAME,
                sink=SINK_NAME_INFLUX,
                duration_sec=duration,
                n_records=n,
                trigger=trigger,
                error=error_type,
            )
            self._buffer.clear()
            self._last_flush = time.time()

    def close(self):
        try:
            self._flush_influx(trigger="close")
            self._r.close()
            self._influx_client.close()
        except Exception as e:
            log.error("[Indicators] close error: %s", e)

    def _ema(self, symbol, close_price, period):
        sym_state = self._ema_state.setdefault(symbol, {})
        if period not in sym_state:
            sym_state[period] = close_price
            return close_price
        k = 2.0 / (period + 1)
        prev = sym_state[period]
        new_ema = close_price * k + prev * (1 - k)
        sym_state[period] = new_ema
        return new_ema

    def _macd_signal(self, state_key, macd_value, period=9):
        if state_key not in self._macd_signal_state:
            self._macd_signal_state[state_key] = macd_value
            return macd_value
        k = 2.0 / (period + 1)
        prev = self._macd_signal_state[state_key]
        next_signal = macd_value * k + prev * (1 - k)
        self._macd_signal_state[state_key] = next_signal
        return next_signal

    def flat_map(self, value):
        try:
            if isinstance(value, (str, bytes)):
                deserialize_start = time.monotonic()
                value = json.loads(value)
                record_kafka_source_deserialize(
                    topic=SOURCE_TOPIC, duration_sec=time.monotonic() - deserialize_start
                )

            if not value.get("is_closed"):
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason="not_closed")
                return iter([])

            symbol = value.get("symbol")
            if not symbol:
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason="missing_symbol")
                return iter([])

            exchange = value.get("exchange", "binance")
            interval = value.get("interval", "1m")
            state_key = f"{exchange}:{symbol}:{interval}"

            close_price = float(value["close"])
            kline_start = int(value["kline_start"])
            high_price = float(value["high"])
            low_price = float(value["low"])
            volume = float(value.get("volume", 0.0))

            # First-time-encountered key → record new key + start warmup
            if state_key not in self._closes:
                self._closes[state_key] = deque(maxlen=self.MAX_HISTORY)
                self._volumes[state_key] = deque(maxlen=self.MAX_HISTORY)
                self._candles[state_key] = deque(maxlen=self.MAX_HISTORY)
                record_writer_new_key(writer=WRITER_NAME, exchange=f"{exchange}:{interval}")

            self._closes[state_key].append(close_price)
            self._volumes[state_key].append(volume)
            self._candles[state_key].append({
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            })

            prices = self._closes[state_key]
            volumes = self._volumes[state_key]
            candles = self._candles[state_key]

            sma20 = self._sma(prices, 20)
            sma50 = self._sma(prices, 50)
            ema12 = self._ema(state_key, close_price, 12)
            ema26 = self._ema(state_key, close_price, 26)
            rsi14 = self._rsi(prices, 14)
            bb_middle, bb_upper, bb_lower, bb_width = self._bollinger(prices, 20, 2.0)
            volume_sma20 = self._sma(volumes, 20)
            macd = ema12 - ema26
            macd_signal = self._macd_signal(state_key, macd, 9)
            macd_histogram = macd - macd_signal
            atr14 = self._atr(candles, 14)

            # Record indicator recomputations (B7 + observability)
            record_indicator_recompute(indicator="sma20", trigger="new_candle")
            record_indicator_recompute(indicator="sma50", trigger="new_candle")
            record_indicator_recompute(indicator="ema12", trigger="new_candle")
            record_indicator_recompute(indicator="ema26", trigger="new_candle")
            record_indicator_recompute(indicator="rsi14", trigger="new_candle")
            record_indicator_recompute(indicator="bollinger", trigger="new_candle")
            record_indicator_recompute(indicator="macd", trigger="new_candle")
            record_indicator_recompute(indicator="atr14", trigger="new_candle")

            # Write to KeyDB
            mapping = {
                "timestamp": kline_start,
                "interval": interval,
                "close": round(close_price, 8),
                "high": round(high_price, 8),
                "low": round(low_price, 8),
                "volume": round(volume, 8),
            }
            if sma20 is not None:
                mapping["sma20"] = round(sma20, 8)
            if sma50 is not None:
                mapping["sma50"] = round(sma50, 8)
            mapping["ema12"] = round(ema12, 8)
            mapping["ema26"] = round(ema26, 8)
            if rsi14 is not None:
                mapping["rsi14"] = round(rsi14, 8)
            if bb_middle is not None:
                mapping["bb_middle"] = round(bb_middle, 8)
                mapping["bb_upper"] = round(bb_upper, 8)
                mapping["bb_lower"] = round(bb_lower, 8)
                mapping["bb_width"] = round(bb_width, 8)
            if volume_sma20 is not None:
                mapping["volume_sma20"] = round(volume_sma20, 8)
            if atr14 is not None:
                mapping["atr14"] = round(atr14, 8)
            mapping["macd"] = round(macd, 8)
            mapping["macd_signal"] = round(macd_signal, 8)
            mapping["macd_histogram"] = round(macd_histogram, 8)

            latest_key = f"indicator:latest:{exchange}:{symbol}:{interval}"
            legacy_key = f"indicator:latest:{exchange}:{symbol}"
            history_key = f"indicator:history:{exchange}:{symbol}:{interval}"

            redis_start = time.monotonic()
            redis_error: str | None = None
            try:
                self._r.hset(latest_key, mapping=mapping)
                self._r.expire(latest_key, self._history_ttl_sec)
                self._r.hset(legacy_key, mapping=mapping)
                self._r.expire(legacy_key, self._history_ttl_sec)

                history_snapshot = {
                    "exchange": exchange,
                    "symbol": symbol,
                    "interval": interval,
                    "timestamp": kline_start,
                    **mapping,
                }
                history_json = json.dumps(history_snapshot, separators=(",", ":"))
                self._r.zremrangebyscore(history_key, kline_start, kline_start)
                self._r.zadd(history_key, {history_json: kline_start})
                self._r.expire(history_key, self._history_ttl_sec)
                count = self._history_write_count.get(history_key, 0) + 1
                self._history_write_count[history_key] = count
                if count % self._history_max_entries == 0:
                    self._r.zremrangebyrank(history_key, 0, -self._history_max_entries - 1)
            except Exception as e:
                redis_error = type(e).__name__
                raise
            finally:
                redis_duration = time.monotonic() - redis_start
                # Log every write as a single-record flush so we can
                # see per-symbol Redis write latency in dashboards.
                record_flush(
                    writer=WRITER_NAME,
                    sink=SINK_NAME_REDIS,
                    duration_sec=redis_duration,
                    n_records=1,
                    trigger="inline",
                    error=redis_error,
                )

            # Write to InfluxDB
            point = Point("indicators").tag("symbol", symbol).tag("exchange", exchange)
            if sma20 is not None:
                point = point.field("sma20", round(sma20, 8))
            if sma50 is not None:
                point = point.field("sma50", round(sma50, 8))
            if rsi14 is not None:
                point = point.field("rsi14", round(rsi14, 8))
            if bb_middle is not None:
                point = (
                    point
                    .field("bb_middle", round(bb_middle, 8))
                    .field("bb_upper", round(bb_upper, 8))
                    .field("bb_lower", round(bb_lower, 8))
                    .field("bb_width", round(bb_width, 8))
                )
            if volume_sma20 is not None:
                point = point.field("volume_sma20", round(volume_sma20, 8))
            if atr14 is not None:
                point = point.field("atr14", round(atr14, 8))
            point = (
                point
                .field("ema12", round(ema12, 8))
                .field("ema26", round(ema26, 8))
                .field("macd", round(macd, 8))
                .field("macd_signal", round(macd_signal, 8))
                .field("macd_histogram", round(macd_histogram, 8))
                .field("close", close_price)
                .time(kline_start, WritePrecision.MS)
            )
            self._buffer.append(point)
            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=kline_start / 1000.0,
            )
            record_buffer_size(WRITER_NAME, SINK_NAME_INFLUX, len(self._buffer))

            # Snapshot state-key gauges on every emit (cheap; one set call)
            self._record_state_keys()

            # B7 warmup tracking: record the warmup duration once we've
            # seen the first new candle for a key after open(). This is a
            # proxy for the EMA / MACD state warmup cost.
            if not self._warmup_recorded:
                self._first_candles_seen.add(state_key)
                # We consider warmup "complete" once we've seen at least
                # one new candle for any key (Flink re-hydrates the rest
                # asynchronously from Kafka offsets).
                if len(self._first_candles_seen) >= 1:
                    warmup_duration = time.monotonic() - self._open_time
                    record_indicator_warmup(state_type="ema", duration_sec=warmup_duration)
                    record_indicator_warmup(state_type="macd_signal", duration_sec=warmup_duration)
                    record_indicator_warmup(state_type="candle_deque", duration_sec=warmup_duration)
                    self._warmup_recorded = True

            if len(self._buffer) >= 200 or (time.time() - self._last_flush) >= 5.0:
                self._flush_influx(trigger="size" if len(self._buffer) >= 200 else "time")
                # B7 — persist the in-process state to Redis so a
                # restart can pick up where we left off.
                self._persist_state(exchange)

        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[Indicators] flat_map error | symbol=%s error=%s", s, e)
            try:
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
            except Exception as metric_exc:
                # Never let a metric hiccup hide the real error.
                # We log at DEBUG because the parent ``log.error``
                # already carries the user-facing information.
                log.debug("[Indicators] metric record failed: %s", metric_exc)
        return iter([])

    def _persist_state(self, exchange: str) -> None:
        """Snapshot the writer's in-process dicts to Redis (B7).

        Called after every flush_influx. The snapshot is small
        (≤256KB per symbol) and the write is fire-and-forget: a
        Redis hiccup does not block the indicator pipeline.
        """
        if not hasattr(self, "_state_store"):
            return
        # Lazy first-touch hydrate (B7).
        if exchange not in self._hydrated_exchanges:
            self._state_store.hydrate_writer(self, exchange)
            self._hydrated_exchanges.add(exchange)
        snapshots = self._state_store.snapshot_writer(self)
        if not snapshots:
            return
        try:
            self._state_store.save_batch(exchange, snapshots)
        except Exception as exc:
            log.warning("[Indicators] state persist failed | exchange=%s error=%s",
                       exchange, exc)
