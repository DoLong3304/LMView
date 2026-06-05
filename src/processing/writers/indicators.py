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

INFLUX_URL    = os.environ.get("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.environ.get("INFLUX_ORG",    "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

log = logging.getLogger(__name__)


class IndicatorWriter(FlatMapFunction):
    """Computes SMA/EMA indicators from closed 1m klines.

    Outputs:
        - ``indicator:latest:{exchange}:{symbol}`` hash in Redis Sentinel
        - ``indicators`` measurement in InfluxDB
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

    def _flush_influx(self):
        if not self._buffer:
            return
        try:
            self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=self._buffer)
        except Exception as e:
            log.error("[Indicators/InfluxDB] flush error: %s", e)
        finally:
            self._buffer.clear()
            self._last_flush = time.time()

    def close(self):
        try:
            self._flush_influx()
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
                value = json.loads(value)

            if not value.get("is_closed"):
                return []

            symbol = value.get("symbol")
            if not symbol:
                return []

            exchange = value.get("exchange", "binance")
            interval = value.get("interval", "1m")
            state_key = f"{exchange}:{symbol}:{interval}"

            close_price = float(value["close"])
            kline_start = int(value["kline_start"])
            high_price = float(value["high"])
            low_price = float(value["low"])
            volume = float(value.get("volume", 0.0))

            if state_key not in self._closes:
                self._closes[state_key] = deque(maxlen=self.MAX_HISTORY)
                self._volumes[state_key] = deque(maxlen=self.MAX_HISTORY)
                self._candles[state_key] = deque(maxlen=self.MAX_HISTORY)
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
            if len(self._buffer) >= 200 or (time.time() - self._last_flush) >= 5.0:
                self._flush_influx()

        except Exception as e:
            s = value.get("symbol") if isinstance(value, dict) else "unknown"
            log.error("[Indicators] flat_map error | symbol=%s error=%s", s, e)
        return []
