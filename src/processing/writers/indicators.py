"""
Technical indicator writer for Flink stream processing.

Receives closed 1m klines, maintains rolling close-price buffers per symbol,
computes SMA20, SMA50, EMA12, EMA26, RSI14, Bollinger Bands, MACD, ATR14,
VWAP, Stochastic, MFI, Ichimoku Cloud, Supertrend, Parabolic SAR,
and writes results to Redis Sentinel + InfluxDB.
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
    """Computes technical indicators from closed 1m klines.

    Outputs:
        - ``indicator:latest:{exchange}:{symbol}`` hash in Redis Sentinel
        - ``indicators`` measurement in InfluxDB

    Computed indicators (v0.25.54+):
        Trend: SMA20, SMA50, EMA12, EMA26, VWAP, Ichimoku Cloud (conv/base/spanA/spanB), Supertrend, PSAR
        Momentum: RSI14, MACD (line/signal/histogram), Stochastic (%K/%D), MFI
        Volatility: Bollinger Bands (upper/middle/lower/width), ATR14
        Volume: Volume SMA20
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

    # ── New indicators (v0.25.54+) ────────────────────────────────────────

    def _vwap(self, state_key, typical_price, volume, timestamp_ms):
        """Volume-Weighted Average Price — resets daily (UTC midnight)."""
        state = self._vwap_state.get(state_key, {"tpv": 0.0, "vol": 0.0, "day": 0})
        day = timestamp_ms // 86400000  # ms → UTC day number
        if day != state["day"]:
            state = {"tpv": 0.0, "vol": 0.0, "day": day}
        state["tpv"] += typical_price * volume
        state["vol"] += volume
        self._vwap_state[state_key] = state
        if state["vol"] == 0:
            return None
        return state["tpv"] / state["vol"]

    def _stochastic(self, state_key, close, high, low, period=14):
        """Stochastic %K — rolling window high/low."""
        sym_highs = self._highs.setdefault(state_key, deque(maxlen=self.MAX_HISTORY))
        sym_lows = self._lows.setdefault(state_key, deque(maxlen=self.MAX_HISTORY))
        sym_highs.append(high)
        sym_lows.append(low)
        if len(sym_highs) < period:
            return None
        window_highs = list(sym_highs)[-period:]
        window_lows = list(sym_lows)[-period:]
        highest = max(window_highs)
        lowest = min(window_lows)
        if highest == lowest:
            return 50.0
        return ((close - lowest) / (highest - lowest)) * 100.0

    def _stochastic_d(self, state_key, k_value, period=3):
        """Stochastic %D — SMA of last 3 %K values."""
        state = self._stoch_d_state.setdefault(state_key, deque(maxlen=period))
        state.append(k_value)
        if len(state) < period:
            return None
        return sum(state) / period

    def _mfi(self, state_key, candles, period=14):
        """Money Flow Index — typical_price × volume flow ratio."""
        rows = list(candles)
        if len(rows) < period + 1:
            return None
        window = rows[-(period + 1):]
        pos_flow = 0.0
        neg_flow = 0.0
        for i in range(1, len(window)):
            tp = (window[i]["high"] + window[i]["low"] + window[i]["close"]) / 3.0
            prev_tp = (window[i - 1]["high"] + window[i - 1]["low"] + window[i - 1]["close"]) / 3.0
            mf = tp * window[i]["volume"]
            if tp > prev_tp:
                pos_flow += mf
            else:
                neg_flow += mf
        if neg_flow == 0.0:
            return 100.0
        ratio = pos_flow / neg_flow
        return 100.0 - (100.0 / (1.0 + ratio))

    @staticmethod
    def _ichimoku(candles, conv_period=9, base_period=26, span_period=52):
        """Ichimoku Cloud — conversion, base, spanA, spanB lines."""
        rows = list(candles)
        if len(rows) < base_period:
            return None, None, None, None
        conv_window = rows[-conv_period:]
        conv = (max(c["high"] for c in conv_window) + min(c["low"] for c in conv_window)) / 2.0
        base_window = rows[-base_period:]
        base = (max(c["high"] for c in base_window) + min(c["low"] for c in base_window)) / 2.0
        span_a = (conv + base) / 2.0
        span_b_window = rows[-span_period:] if len(rows) >= span_period else rows
        span_b = (max(c["high"] for c in span_b_window) + min(c["low"] for c in span_b_window)) / 2.0
        return conv, base, span_a, span_b

    def _supertrend(self, state_key, candles, atr_val, period=10, multiplier=3.0):
        """Supertrend — trend-following with state."""
        rows = list(candles)
        if atr_val is None or len(rows) < 2:
            return None
        cur = rows[-1]
        prev = rows[-2]
        hl2 = (cur["high"] + cur["low"]) / 2.0
        basic_upper = hl2 + multiplier * atr_val
        basic_lower = hl2 - multiplier * atr_val
        state = self._supertrend_state.get(state_key)
        if state is None:
            state = {"final_upper": basic_upper, "final_lower": basic_lower, "in_uptrend": cur["close"] > basic_upper}
            self._supertrend_state[state_key] = state
        else:
            st_upper = basic_upper if basic_upper < state["final_upper"] or prev["close"] > state["final_upper"] else state["final_upper"]
            st_lower = basic_lower if basic_lower > state["final_lower"] or prev["close"] < state["final_lower"] else state["final_lower"]
            state["final_upper"] = st_upper
            state["final_lower"] = st_lower
            if cur["close"] > st_upper:
                state["in_uptrend"] = True
            elif cur["close"] < st_lower:
                state["in_uptrend"] = False
            self._supertrend_state[state_key] = state
        return state["final_lower"] if state["in_uptrend"] else state["final_upper"]

    def _psar(self, state_key, close, high, low):
        """Parabolic SAR — step-based with acceleration."""
        if state_key not in self._highs or len(self._highs[state_key]) < 2:
            return None
        state = self._psar_state.get(state_key)
        if state is None:
            prev_high = list(self._highs[state_key])[-2]
            rising = close >= prev_high
            state = {
                "rising": rising,
                "acceleration": 0.02,
                "extreme_point": high if rising else low,
                "sar": low if rising else high,
            }
            self._psar_state[state_key] = state
        prev_sar = state["sar"]
        sar = prev_sar + state["acceleration"] * (state["extreme_point"] - prev_sar)
        prev_high = self._highs[state_key][-2] if len(self._highs[state_key]) >= 2 else high
        prev_low = self._lows[state_key][-2] if state_key in self._lows and len(self._lows[state_key]) >= 2 else low
        if state["rising"]:
            sar = min(sar, prev_high, high)
            if low < sar:
                state["rising"] = False
                state["sar"] = state["extreme_point"]
                state["extreme_point"] = low
                state["acceleration"] = 0.02
            elif high > state["extreme_point"]:
                state["extreme_point"] = high
                state["acceleration"] = min(state["acceleration"] + 0.02, 0.2)
        else:
            sar = max(sar, prev_low, low)
            if high > sar:
                state["rising"] = True
                state["sar"] = state["extreme_point"]
                state["extreme_point"] = high
                state["acceleration"] = 0.02
            elif low < state["extreme_point"]:
                state["extreme_point"] = low
                state["acceleration"] = min(state["acceleration"] + 0.02, 0.2)
        state["sar"] = sar
        self._psar_state[state_key] = state
        return sar

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
        # New indicator states (v0.25.54+)
        self._vwap_state: dict[str, dict] = {}
        self._stoch_d_state: dict[str, deque] = {}
        self._supertrend_state: dict[str, dict] = {}
        self._psar_state: dict[str, dict] = {}
        self._highs: dict[str, deque] = {}
        self._lows: dict[str, deque] = {}
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
        self._hydrated_exchanges: set[str] = set()

        self._open_time = time.monotonic()
        self._first_candles_seen: set[str] = set()
        self._warmup_recorded = False
        init_metrics()

    def _record_state_keys(self) -> None:
        """Snapshot the in-memory state-key gauges."""
        try:
            closes = len(self._closes)
            volumes = len(self._volumes)
            candles = len(self._candles)
            ema = len(self._ema_state)
            macd = len(self._macd_signal_state)
            INDICATOR_STATE_KEYS.labels(state_type="candle_deque").set(candles)
            INDICATOR_STATE_KEYS.labels(state_type="closes_deque").set(closes)
            INDICATOR_STATE_KEYS.labels(state_type="volumes_deque").set(volumes)
            INDICATOR_STATE_KEYS.labels(state_type="ema_state").set(ema)
            INDICATOR_STATE_KEYS.labels(state_type="macd_signal").set(macd)
        except Exception as e:
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
            typical_price = (high_price + low_price + close_price) / 3.0

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
                "kline_start": kline_start,
            })

            prices = self._closes[state_key]
            volumes = self._volumes[state_key]
            candles = self._candles[state_key]

            # ── Core indicators ────────────────────────────────────────────
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

            # ── New indicators (v0.25.54+) ────────────────────────────────
            vwap = self._vwap(state_key, typical_price, volume, kline_start)

            stoch_k = self._stochastic(state_key, close_price, high_price, low_price, 14)
            stoch_d = self._stochastic_d(state_key, stoch_k, 3) if stoch_k is not None else None

            mfi = self._mfi(state_key, candles, 14)

            ichi_conv, ichi_base, ichi_span_a, ichi_span_b = None, None, None, None
            if len(candles) >= 26:
                ichi_conv, ichi_base, ichi_span_a, ichi_span_b = self._ichimoku(candles, 9, 26, 52)

            supertrend = self._supertrend(state_key, candles, atr14, 10, 3.0)

            psar = self._psar(state_key, close_price, high_price, low_price)

            # Record indicator recomputations
            record_indicator_recompute(indicator="sma20", trigger="new_candle")
            record_indicator_recompute(indicator="sma50", trigger="new_candle")
            record_indicator_recompute(indicator="ema12", trigger="new_candle")
            record_indicator_recompute(indicator="ema26", trigger="new_candle")
            record_indicator_recompute(indicator="rsi14", trigger="new_candle")
            record_indicator_recompute(indicator="bollinger", trigger="new_candle")
            record_indicator_recompute(indicator="macd", trigger="new_candle")
            record_indicator_recompute(indicator="atr14", trigger="new_candle")
            record_indicator_recompute(indicator="vwap", trigger="new_candle")
            record_indicator_recompute(indicator="stochastic", trigger="new_candle")
            record_indicator_recompute(indicator="mfi", trigger="new_candle")
            record_indicator_recompute(indicator="ichimoku", trigger="new_candle")
            record_indicator_recompute(indicator="supertrend", trigger="new_candle")
            record_indicator_recompute(indicator="psar", trigger="new_candle")

            # ── Write to Redis (KeyDB) ────────────────────────────────────
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

            # New indicator fields (v0.25.54+)
            if vwap is not None:
                mapping["vwap"] = round(vwap, 8)
            if stoch_k is not None:
                mapping["stoch_k"] = round(stoch_k, 8)
            if stoch_d is not None:
                mapping["stoch_d"] = round(stoch_d, 8)
            if mfi is not None:
                mapping["mfi"] = round(mfi, 8)
            if ichi_conv is not None:
                mapping["ichi_conversion"] = round(ichi_conv, 8)
                mapping["ichi_base"] = round(ichi_base, 8)
                mapping["ichi_span_a"] = round(ichi_span_a, 8)
                mapping["ichi_span_b"] = round(ichi_span_b, 8)
            if supertrend is not None:
                mapping["supertrend"] = round(supertrend, 8)
            if psar is not None:
                mapping["psar"] = round(psar, 8)

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
                record_flush(
                    writer=WRITER_NAME,
                    sink=SINK_NAME_REDIS,
                    duration_sec=redis_duration,
                    n_records=1,
                    trigger="inline",
                    error=redis_error,
                )

            # ── Write to InfluxDB ─────────────────────────────────────────
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
            # New InfluxDB fields
            if vwap is not None:
                point = point.field("vwap", round(vwap, 8))
            if stoch_k is not None:
                point = point.field("stoch_k", round(stoch_k, 8))
            if stoch_d is not None:
                point = point.field("stoch_d", round(stoch_d, 8))
            if mfi is not None:
                point = point.field("mfi", round(mfi, 8))
            if ichi_conv is not None:
                point = (
                    point
                    .field("ichi_conversion", round(ichi_conv, 8))
                    .field("ichi_base", round(ichi_base, 8))
                    .field("ichi_span_a", round(ichi_span_a, 8))
                    .field("ichi_span_b", round(ichi_span_b, 8))
                )
            if supertrend is not None:
                point = point.field("supertrend", round(supertrend, 8))
            if psar is not None:
                point = point.field("psar", round(psar, 8))
            self._buffer.append(point)

            record_kafka_source(topic=SOURCE_TOPIC, partition=0, n=1)
            record_writer_event_time(
                writer=WRITER_NAME, exchange=exchange, symbol=symbol,
                event_ts=kline_start / 1000.0,
            )
            record_buffer_size(WRITER_NAME, SINK_NAME_INFLUX, len(self._buffer))
            self._record_state_keys()

            # B7 warmup tracking
            if not self._warmup_recorded:
                self._first_candles_seen.add(state_key)
                if len(self._first_candles_seen) >= 1:
                    warmup_duration = time.monotonic() - self._open_time
                    record_indicator_warmup(state_type="ema", duration_sec=warmup_duration)
                    record_indicator_warmup(state_type="macd_signal", duration_sec=warmup_duration)
                    record_indicator_warmup(state_type="candle_deque", duration_sec=warmup_duration)
                    self._warmup_recorded = True

            if len(self._buffer) >= 200 or (time.time() - self._last_flush) >= 5.0:
                self._flush_influx(trigger="size" if len(self._buffer) >= 200 else "time")
                self._persist_state(exchange)

        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[Indicators] flat_map error | symbol=%s error=%s", s, e)
            try:
                record_kafka_source_drop(topic=SOURCE_TOPIC, reason=type(e).__name__)
            except Exception as metric_exc:
                log.debug("[Indicators] metric record failed: %s", metric_exc)
        return iter([])

    def _persist_state(self, exchange: str) -> None:
        if not hasattr(self, "_state_store"):
            return
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
