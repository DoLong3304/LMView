"""
Indicator service — expanded indicator backend for Phase 0.

Provides indicator listing, latest values from Redis, and extensible
compute-from-candle-history for future expansion.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from backend.core.constants import INFLUX_1M_RETENTION_DAYS, MAX_RAW_CANDLES
from backend.core.database import get_redis
from backend.models.common import DataFreshness
from backend.models.indicators import (
    IndicatorPoint,
    IndicatorSnapshot,
    IndicatorSeriesResponse,
    IndicatorSummary,
    SupportedIndicator,
)
from backend.services.candle_service import (
    aggregate,
    collect_base_1m_candles,
    merge_unique,
    validate_interval,
    validate_symbol,
)

logger = logging.getLogger("backend.services.indicator_service")

# ── Supported indicators catalog ──────────────────────────────────────────────

SUPPORTED_INDICATORS: List[SupportedIndicator] = [
    SupportedIndicator(
        name="sma20", display_name="SMA 20",
        category="trend", default_params={"period": 20},
    ),
    SupportedIndicator(
        name="sma50", display_name="SMA 50",
        category="trend", default_params={"period": 50},
    ),
    SupportedIndicator(
        name="ema12", display_name="EMA 12",
        category="trend", default_params={"period": 12},
    ),
    SupportedIndicator(
        name="ema26", display_name="EMA 26",
        category="trend", default_params={"period": 26},
    ),
    SupportedIndicator(
        name="rsi", display_name="RSI (14)",
        category="momentum", default_params={"period": 14},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="macd", display_name="MACD",
        category="momentum", default_params={"fast": 12, "slow": 26, "signal": 9},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="bollinger_bands", display_name="Bollinger Bands",
        category="volatility", default_params={"period": 20, "std_dev": 2},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="bb", display_name="Bollinger Bands",
        category="volatility", default_params={"period": 20, "std_dev": 2},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="vwap", display_name="VWAP",
        category="volume", default_params={},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="atr", display_name="ATR (14)",
        category="volatility", default_params={"period": 14},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="volume_ma", display_name="Volume MA",
        category="volume", default_params={"period": 20},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="volumeMa", display_name="Volume MA",
        category="volume", default_params={"period": 20},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="stochastic", display_name="Stochastic",
        category="momentum", default_params={"k": 14, "d": 3},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="mfi", display_name="MFI",
        category="momentum", default_params={"period": 14},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="ichimoku", display_name="Ichimoku Cloud",
        category="trend", default_params={"conversion": 9, "base": 26, "span": 52},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="supertrend", display_name="Supertrend",
        category="trend", default_params={"period": 10, "multiplier": 3},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="psar", display_name="Parabolic SAR",
        category="trend", default_params={"step": 0.02, "max_step": 0.2},
        available_sources=["computed"],
    ),
    SupportedIndicator(
        name="volume", display_name="Volume",
        category="volume", default_params={},
        available_sources=["redis", "computed"],
    ),
    SupportedIndicator(
        name="support_resistance", display_name="Support / Resistance",
        category="levels", default_params={"lookback": 120},
        available_sources=["future"],
    ),
    SupportedIndicator(
        name="whale_alert", display_name="Whale Alert",
        category="alerts", default_params={"min_notional_usd": 1000000},
        available_sources=["future"],
    ),
]

SUPPORTED_NAMES = {ind.name for ind in SUPPORTED_INDICATORS}

SERIES_SUPPORTED_NAMES = {
    "sma20",
    "sma50",
    "ema12",
    "ema26",
    "rsi",
    "macd",
    "bb",
    "volume",
    "volumeMa",
    "atr",
    "vwap",
    "stochastic",
    "mfi",
    "ichimoku",
    "supertrend",
    "psar",
}

SERIES_NAME_ALIASES = {
    "bollinger": "bb",
    "bollinger_bands": "bb",
    "rsi14": "rsi",
    "atr14": "atr",
    "volume_ma": "volumeMa",
    "volume_sma20": "volumeMa",
}

INDICATOR_REQUIRED_CANDLES = {
    "sma20": 20,
    "sma50": 50,
    "ema12": 12,
    "ema26": 26,
    "rsi": 15,
    "macd": 35,
    "bb": 20,
    "volume": 1,
    "volumeMa": 20,
    "atr": 15,
    "vwap": 1,
    "stochastic": 15,
    "mfi": 15,
    "ichimoku": 53,
    "supertrend": 15,
    "psar": 3,
}

DEFAULT_SERIES_INDICATORS = [
    "sma20",
    "sma50",
    "ema12",
    "ema26",
    "rsi",
    "macd",
    "bb",
    "volume",
    "volumeMa",
    "atr",
    "vwap",
    "stochastic",
    "mfi",
    "ichimoku",
    "supertrend",
    "psar",
]

WARN_NOT_ENOUGH = "not_enough_candle_data"
WARN_UNAVAILABLE = "indicator_data_unavailable"
WARN_EMPTY = "backend_returned_empty_result"


def get_supported_indicators() -> List[SupportedIndicator]:
    """Return list of all supported indicators."""
    return SUPPORTED_INDICATORS


def _normalize_requested_indicators(indicators: Sequence[str] | None) -> List[str]:
    """Normalize user-facing aliases to the backend series groups."""
    if not indicators:
        return list(DEFAULT_SERIES_INDICATORS)

    normalized: List[str] = []
    for item in indicators:
        for raw in str(item).split(","):
            key = raw.strip()
            if not key:
                continue
            canonical = SERIES_NAME_ALIASES.get(key, key)
            if canonical in SERIES_SUPPORTED_NAMES and canonical not in normalized:
                normalized.append(canonical)

    return normalized or list(DEFAULT_SERIES_INDICATORS)


def _required_candle_count(indicators: Sequence[str]) -> int:
    """Return the maximum candle count needed by requested indicators."""
    return max((INDICATOR_REQUIRED_CANDLES.get(name, 1) for name in indicators), default=1)


def _decode_redis_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _parse_candle_payload(payload: Any) -> Optional[dict]:
    """Convert Redis/JSON candle payloads to the shared candle row shape."""
    try:
        if isinstance(payload, tuple):
            payload = payload[0]
        payload = _decode_redis_value(payload)
        raw = json.loads(payload) if isinstance(payload, str) else payload
        if not isinstance(raw, dict):
            return None

        timestamp = raw.get("openTime", raw.get("t", raw.get("timestamp")))
        if timestamp is None:
            return None
        return {
            "openTime": int(float(timestamp)),
            "open": float(raw.get("open", raw.get("o"))),
            "high": float(raw.get("high", raw.get("h"))),
            "low": float(raw.get("low", raw.get("l"))),
            "close": float(raw.get("close", raw.get("c"))),
            "volume": float(raw.get("volume", raw.get("v", 0))),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


async def _read_redis_base_candles(
    symbol: str,
    exchange: str,
    limit: int,
) -> List[dict]:
    """Read recent 1m candles from Redis sorted-set cache."""
    r = await get_redis()
    history_key = f"candle:1m:{exchange}:{symbol}"
    try:
        raw_candles = await r.zrevrange(history_key, 0, max(limit - 1, 0), withscores=True)
    except Exception as exc:
        logger.warning("[IndicatorFallback] Redis candle read failed: %s", exc)
        return []

    candles = [
        candle
        for candle in (_parse_candle_payload(item) for item in raw_candles or [])
        if candle is not None
    ]
    return merge_unique([], candles)


async def _fetch_indicator_candles(
    symbol: str,
    exchange: str,
    interval: str,
    target_sec: int,
    limit: int,
    required: int,
    allow_storage: bool,
) -> tuple[List[dict], List[str], List[str]]:
    """Fetch candle rows from Redis first, then Influx/Trino storage when allowed."""
    if interval == "1s":
        return [], [], [WARN_UNAVAILABLE]

    aggregate_limit = max(limit, required, 1)
    multiplier = max(target_sec // 60, 1)
    raw_limit = min((aggregate_limit * multiplier) + multiplier, MAX_RAW_CANDLES)

    sources: List[str] = []
    warnings: List[str] = []
    base_candles = await _read_redis_base_candles(symbol, exchange, raw_limit)
    if base_candles:
        sources.append("redis_candles")

    current = base_candles if target_sec == 60 else aggregate(base_candles, target_sec * 1000)
    if allow_storage and len(current) < aggregate_limit:
        now_ms = int(time.time() * 1000)
        influx_cutoff_ms = now_ms - (INFLUX_1M_RETENTION_DAYS * 24 * 60 * 60 * 1000)
        try:
            storage_candles = await asyncio.to_thread(
                collect_base_1m_candles,
                symbol,
                target_sec,
                aggregate_limit,
                now_ms,
                now_ms,
                influx_cutoff_ms,
            )
        except Exception as exc:
            logger.warning("[IndicatorFallback] Influx/Trino candle fallback failed: %s", exc)
            storage_candles = []

        if storage_candles:
            base_candles = merge_unique(base_candles, storage_candles)
            sources.append("influx_trino_candles")

    candles = base_candles if target_sec == 60 else aggregate(base_candles, target_sec * 1000)
    candles = candles[-aggregate_limit:]
    if not candles:
        warnings.append(WARN_UNAVAILABLE)
    return candles, sources, warnings


def _point(timestamp: int, value: float | int | None) -> Optional[IndicatorPoint]:
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return IndicatorPoint(timestamp=int(timestamp), value=round(numeric, 8))


def _series_latest(points: Sequence[IndicatorPoint]) -> Optional[float]:
    return points[-1].value if points else None


def _sma_series(candles: Sequence[dict], period: int, field: str = "close") -> List[IndicatorPoint]:
    if len(candles) < period:
        return []
    out: List[IndicatorPoint] = []
    running = 0.0
    for index, candle in enumerate(candles):
        running += float(candle[field])
        if index >= period:
            running -= float(candles[index - period][field])
        if index >= period - 1:
            point = _point(candle["openTime"], running / period)
            if point:
                out.append(point)
    return out


def _ema_series(candles: Sequence[dict], period: int, field: str = "close") -> List[IndicatorPoint]:
    if len(candles) < period:
        return []
    values = [float(candle[field]) for candle in candles]
    multiplier = 2 / (period + 1)
    ema = sum(values[:period]) / period
    out = [_point(candles[period - 1]["openTime"], ema)]
    for index in range(period, len(candles)):
        ema = values[index] * multiplier + ema * (1 - multiplier)
        out.append(_point(candles[index]["openTime"], ema))
    return [point for point in out if point is not None]


def _ema_points(points: Sequence[IndicatorPoint], period: int) -> List[IndicatorPoint]:
    if len(points) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = sum(point.value for point in points[:period]) / period
    out = [_point(points[period - 1].timestamp, ema)]
    for index in range(period, len(points)):
        ema = points[index].value * multiplier + ema * (1 - multiplier)
        out.append(_point(points[index].timestamp, ema))
    return [point for point in out if point is not None]


def _rsi_series(candles: Sequence[dict], period: int = 14) -> List[IndicatorPoint]:
    if len(candles) < period + 1:
        return []
    gains = 0.0
    losses = 0.0
    for index in range(1, period + 1):
        diff = float(candles[index]["close"]) - float(candles[index - 1]["close"])
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period

    def rsi_value() -> float:
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    out: List[IndicatorPoint] = []
    first = _point(candles[period]["openTime"], rsi_value())
    if first:
        out.append(first)

    for index in range(period + 1, len(candles)):
        diff = float(candles[index]["close"]) - float(candles[index - 1]["close"])
        gain = diff if diff > 0 else 0.0
        loss = -diff if diff < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        point = _point(candles[index]["openTime"], rsi_value())
        if point:
            out.append(point)
    return out


def _macd_series(
    candles: Sequence[dict],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Dict[str, List[IndicatorPoint]]:
    fast = _ema_series(candles, fast_period)
    slow = _ema_series(candles, slow_period)
    fast_by_time = {point.timestamp: point.value for point in fast}
    macd_points: List[IndicatorPoint] = []
    for slow_point in slow:
        fast_value = fast_by_time.get(slow_point.timestamp)
        if fast_value is None:
            continue
        point = _point(slow_point.timestamp, fast_value - slow_point.value)
        if point:
            macd_points.append(point)

    signal_points = _ema_points(macd_points, signal_period)
    signal_by_time = {point.timestamp: point.value for point in signal_points}
    histogram_points: List[IndicatorPoint] = []
    for macd_point in macd_points:
        signal_value = signal_by_time.get(macd_point.timestamp)
        if signal_value is None:
            continue
        point = _point(macd_point.timestamp, macd_point.value - signal_value)
        if point:
            histogram_points.append(point)

    return {
        "macd": macd_points,
        "macd_signal": signal_points,
        "macd_histogram": histogram_points,
    }


def _bollinger_series(
    candles: Sequence[dict],
    period: int = 20,
    multiplier: float = 2.0,
) -> Dict[str, List[IndicatorPoint]]:
    if len(candles) < period:
        return {"bb_middle": [], "bb_upper": [], "bb_lower": [], "bb_width": []}

    middle: List[IndicatorPoint] = []
    upper: List[IndicatorPoint] = []
    lower: List[IndicatorPoint] = []
    width: List[IndicatorPoint] = []
    for index in range(period - 1, len(candles)):
        window = candles[index - period + 1:index + 1]
        values = [float(candle["close"]) for candle in window]
        avg = sum(values) / period
        variance = sum((value - avg) ** 2 for value in values) / period
        deviation = math.sqrt(variance) * multiplier
        timestamp = candles[index]["openTime"]
        middle_point = _point(timestamp, avg)
        upper_point = _point(timestamp, avg + deviation)
        lower_point = _point(timestamp, avg - deviation)
        width_point = _point(timestamp, ((deviation * 2) / avg) if avg > 0 else 0)
        if middle_point:
            middle.append(middle_point)
        if upper_point:
            upper.append(upper_point)
        if lower_point:
            lower.append(lower_point)
        if width_point:
            width.append(width_point)

    return {
        "bb_middle": middle,
        "bb_upper": upper,
        "bb_lower": lower,
        "bb_width": width,
    }


def _volume_series(candles: Sequence[dict]) -> List[IndicatorPoint]:
    return [
        point
        for point in (_point(candle["openTime"], float(candle.get("volume", 0))) for candle in candles)
        if point is not None
    ]


def _atr_series(candles: Sequence[dict], period: int = 14) -> List[IndicatorPoint]:
    if len(candles) < period + 1:
        return []
    true_ranges: List[IndicatorPoint] = []
    for index in range(1, len(candles)):
        current = candles[index]
        previous = candles[index - 1]
        high = float(current["high"])
        low = float(current["low"])
        previous_close = float(previous["close"])
        true_range = max(high - low, abs(high - previous_close), abs(low - previous_close))
        point = _point(current["openTime"], true_range)
        if point:
            true_ranges.append(point)

    if len(true_ranges) < period:
        return []

    out: List[IndicatorPoint] = []
    atr = sum(point.value for point in true_ranges[:period]) / period
    first = _point(true_ranges[period - 1].timestamp, atr)
    if first:
        out.append(first)
    for index in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[index].value) / period
        point = _point(true_ranges[index].timestamp, atr)
        if point:
            out.append(point)
    return out


def _calculate_series(
    candles: Sequence[dict],
    requested: Sequence[str],
) -> tuple[Dict[str, List[IndicatorPoint]], Dict[str, Optional[float]]]:
    """Compute all requested indicator series from ascending candle rows."""
    series: Dict[str, List[IndicatorPoint]] = {}

    if "sma20" in requested:
        series["sma20"] = _sma_series(candles, 20)
    if "sma50" in requested:
        series["sma50"] = _sma_series(candles, 50)
    if "ema12" in requested:
        series["ema12"] = _ema_series(candles, 12)
    if "ema26" in requested:
        series["ema26"] = _ema_series(candles, 26)
    if "rsi" in requested:
        rsi = _rsi_series(candles, 14)
        series["rsi"] = rsi
        series["rsi14"] = rsi
    if "macd" in requested:
        series.update(_macd_series(candles))
    if "bb" in requested:
        series.update(_bollinger_series(candles))
    if "volume" in requested:
        series["volume"] = _volume_series(candles)
    if "volumeMa" in requested:
        volume_ma = _sma_series(candles, 20, field="volume")
        series["volumeMa"] = volume_ma
        series["volume_sma20"] = volume_ma
    if "atr" in requested:
        atr = _atr_series(candles, 14)
        series["atr"] = atr
        series["atr14"] = atr

    latest = {key: _series_latest(points) for key, points in series.items()}
    return series, latest


async def _build_indicator_series_response(
    symbol: str,
    exchange: str,
    interval: str,
    indicators: Sequence[str] | None,
    limit: int,
    allow_storage: bool,
) -> IndicatorSeriesResponse:
    """Build a stable series response, using candle-derived fallback when needed."""
    symbol_u = validate_symbol(symbol)
    interval_n, target_sec = validate_interval(interval)
    requested = _normalize_requested_indicators(indicators)
    limit_n = max(1, min(int(limit), 1000))
    required = _required_candle_count(requested)

    candles, sources, warnings = await _fetch_indicator_candles(
        symbol_u,
        exchange,
        interval_n,
        target_sec,
        limit_n,
        required,
        allow_storage,
    )
    series, latest = _calculate_series(candles, requested) if candles else ({}, {})

    if candles and len(candles) < required and WARN_NOT_ENOUGH not in warnings:
        warnings.append(WARN_NOT_ENOUGH)
    if not any(points for points in series.values()) and WARN_EMPTY not in warnings:
        warnings.append(WARN_EMPTY)
    if not sources and WARN_UNAVAILABLE not in warnings:
        warnings.append(WARN_UNAVAILABLE)

    timestamp = int(candles[-1]["openTime"]) if candles else None
    source = "computed_from_" + "+".join(sources) if sources else "unavailable"

    return IndicatorSeriesResponse(
        symbol=symbol_u,
        exchange=exchange,
        interval=interval_n,
        requested=requested,
        series=series,
        latest_values=latest,
        source=source,
        sources=sources,
        candle_count=len(candles),
        required_candles=required,
        warnings=warnings,
        freshness=DataFreshness(
            source=source,
            exchange=exchange,
            event_time=timestamp,
            last_updated=datetime.now(timezone.utc).isoformat(),
            freshness_seconds=((int(time.time() * 1000) - timestamp) / 1000.0) if timestamp else None,
            is_stale=False,
            is_fallback=True,
            warnings=warnings,
        ),
    )


async def get_indicator_series(
    symbol: str,
    exchange: str = "binance",
    interval: str = "1m",
    indicators: Sequence[str] | None = None,
    limit: int = 500,
) -> IndicatorSeriesResponse:
    """Return indicator time series, computed from real candles if cache is empty."""
    return await _build_indicator_series_response(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        indicators=indicators,
        limit=limit,
        allow_storage=True,
    )


async def compute_indicators_from_redis(
    symbol: str,
    exchange: str = "binance",
    interval: str = "1m",
) -> Optional[Dict[str, Any]]:
    """
    Compute latest indicator values from Redis candle data.

    This is the low-latency fallback used by the latest snapshot endpoint. It
    intentionally avoids slower Influx/Trino reads; the series endpoint performs
    the deeper storage fallback.
    """
    try:
        response = await _build_indicator_series_response(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            indicators=DEFAULT_SERIES_INDICATORS,
            limit=160,
            allow_storage=False,
        )
    except Exception as exc:
        logger.error("[IndicatorFallback] Compute error: %s", exc)
        return None

    if response.source == "unavailable" or not response.latest_values:
        logger.debug(
            "[IndicatorFallback] Insufficient kline history for %s %s: %d candles",
            symbol,
            interval,
            response.candle_count,
        )
        return None

    values = response.latest_values
    result: Dict[str, Optional[float]] = {
        "sma20": values.get("sma20"),
        "sma50": values.get("sma50"),
        "ema12": values.get("ema12"),
        "ema26": values.get("ema26"),
        "rsi14": values.get("rsi14") or values.get("rsi"),
        "rsi": values.get("rsi") or values.get("rsi14"),
        "macd": values.get("macd"),
        "macd_signal": values.get("macd_signal"),
        "macd_histogram": values.get("macd_histogram"),
        "bb_middle": values.get("bb_middle"),
        "bb_upper": values.get("bb_upper"),
        "bb_lower": values.get("bb_lower"),
        "bb_width": values.get("bb_width"),
        "volume_sma20": values.get("volume_sma20") or values.get("volumeMa"),
        "volumeMa": values.get("volumeMa") or values.get("volume_sma20"),
        "atr14": values.get("atr14") or values.get("atr"),
        "atr": values.get("atr") or values.get("atr14"),
    }

    latest_candle = response.series.get("volume", [])
    if latest_candle:
        result["volume"] = latest_candle[-1].value

    return result


async def get_indicator_snapshot(
    symbol: str,
    exchange: str = "binance",
    interval: str = "1m",
) -> IndicatorSnapshot:
    """
    Get latest indicator values from Redis, with fallback to Redis-based computation.

    Reads pre-computed indicators from Redis hash first. If unavailable or stale,
    falls back to computing indicators directly from kline history.
    """
    symbol_u = symbol.upper()
    r = await get_redis()
    interval_n = interval.strip().lower() or "1m"

    # Try pre-computed indicators (from Flink)
    data = await r.hgetall(f"indicator:latest:{exchange}:{symbol_u}:{interval_n}")
    if not data:
        data = await r.hgetall(f"indicator:latest:{exchange}:{symbol_u}")
    if not data:
        data = await r.hgetall(f"indicator:latest:{symbol_u}")
    if data:
        data_interval = str(data.get("interval", "1m")).strip().lower()
        if data_interval != interval_n:
            data = {}

    now_ms = int(time.time() * 1000)
    indicators: Dict[str, Optional[float]] = {}
    source = "unavailable"
    timestamp = None

    if data:
        source = "flink_precomputed"
        for field in (
            "sma20", "sma50", "ema12", "ema26",
            "rsi14", "macd", "macd_signal", "macd_histogram",
            "bb_middle", "bb_upper", "bb_lower", "bb_width",
            "volume_sma20", "atr14",
            "close", "high", "low", "volume",
            # New fields (v0.25.54+)
            "vwap", "stoch_k", "stoch_d", "mfi",
            "ichi_conversion", "ichi_base", "ichi_span_a", "ichi_span_b",
            "supertrend", "psar",
        ):
            if field in data:
                try:
                    indicators[field] = float(data[field])
                except (ValueError, TypeError):
                    indicators[field] = None
            else:
                indicators[field] = None

        if "timestamp" in data:
            try:
                timestamp = int(float(data["timestamp"]))
            except (ValueError, TypeError):
                pass

    # Freshness check
    freshness_seconds = None
    is_stale = False
    if timestamp:
        freshness_seconds = (now_ms - timestamp) / 1000.0
        is_stale = freshness_seconds > 120  # Stale after 2 minutes

    # Fallback: compute from Redis kline data if Flink data unavailable or stale
    if source == "unavailable" or is_stale:
        computed = await compute_indicators_from_redis(symbol_u, exchange, interval_n)
        if computed:
            indicators = computed
            source = "redis_derived" if source == "unavailable" else "redis_derived_stale"
            timestamp = now_ms  # Use current time for derived data

    # Provide UI-friendly aliases for fields written by the pipeline.
    if indicators.get("rsi14") is not None:
        indicators.setdefault("rsi", indicators["rsi14"])
    if indicators.get("atr14") is not None:
        indicators.setdefault("atr", indicators["atr14"])
    if indicators.get("volume_sma20") is not None:
        indicators.setdefault("volumeMa", indicators["volume_sma20"])
        indicators.setdefault("volume_ma", indicators["volume_sma20"])
    if indicators.get("bb_middle") is not None:
        indicators.setdefault("bb", indicators["bb_middle"])
        indicators.setdefault("bollinger_bands", indicators["bb_middle"])
    if indicators.get("stoch_k") is not None:
        indicators.setdefault("stochastic", indicators["stoch_k"])
    if indicators.get("ichi_conversion") is not None:
        indicators.setdefault("ichimoku", indicators["ichi_conversion"])

    # Mark still-uncomputed indicators explicitly unavailable
    for ind in ("rsi", "rsi14", "bollinger_bands", "bb", "vwap", "atr", "atr14", "volume_ma", "volumeMa"):
        indicators.setdefault(ind, None)

    return IndicatorSnapshot(
        symbol=symbol_u,
        exchange=exchange,
        interval=interval_n,
        indicators=indicators,
        timestamp=timestamp,
        source=source,
        freshness=DataFreshness(
            source=source,
            exchange=exchange,
            event_time=timestamp,
            freshness_seconds=freshness_seconds,
            is_stale=is_stale,
            is_fallback=source in ("redis_derived", "redis_derived_stale", "unavailable"),
            warnings=["Indicators computed from Redis kline history"] if source == "redis_derived" else [],
        ),
    )


async def get_indicator_summary(
    symbol: str,
    exchange: str = "binance",
    interval: str = "1m",
) -> IndicatorSummary:
    """Get a compact indicator summary for AI context."""
    snapshot = await get_indicator_snapshot(symbol, exchange, interval)

    available = [k for k, v in snapshot.indicators.items() if v is not None]

    return IndicatorSummary(
        symbol=snapshot.symbol,
        exchange=exchange,
        interval=interval,
        available=available,
        latest_values={k: v for k, v in snapshot.indicators.items() if v is not None},
        signals={},  # Phase 1+: compute signals from indicator values
        source=snapshot.source,
        freshness=snapshot.freshness,
    )
