"""
Indicator service — expanded indicator backend for Phase 0.

Provides indicator listing, latest values from Redis, and extensible
compute-from-candle-history for future expansion.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from backend.core.database import get_redis
from backend.models.common import DataFreshness
from backend.models.indicators import (
    IndicatorSnapshot,
    IndicatorSummary,
    SupportedIndicator,
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
]

SUPPORTED_NAMES = {ind.name for ind in SUPPORTED_INDICATORS}


def get_supported_indicators() -> List[SupportedIndicator]:
    """Return list of all supported indicators."""
    return SUPPORTED_INDICATORS


async def compute_indicators_from_redis(
    symbol: str,
    exchange: str = "binance",
    interval: str = "1m",
) -> Optional[Dict[str, Any]]:
    """
    Compute indicators from Redis kline data as fallback when Flink indicators unavailable.

    Reads kline history from Redis and calculates: SMA, EMA, RSI, MACD, Bollinger Bands, ATR.
    Returns dict with computed values, or None if insufficient data.
    """
    try:
        import asyncio
        from backend.core.database import get_redis

        r = await get_redis()
        interval_n = interval.strip().lower() or "1m"

        # Read last N candles from Redis sorted set
        history_key = f"candle:1m:{exchange}:{symbol}"
        candles_raw = await r.zrevrange(history_key, 0, 99, withscores=True)

        if not candles_raw or len(candles_raw) < 20:
            logger.debug("[IndicatorFallback] Insufficient kline history: %d candles", len(candles_raw) if candles_raw else 0)
            return None

        # Parse candles
        closes = []
        highs = []
        lows = []
        volumes = []
        for candle_json, _ in candles_raw:
            try:
                c = json.loads(candle_json)
                closes.append(float(c.get("c", 0)))
                highs.append(float(c.get("h", 0)))
                lows.append(float(c.get("l", 0)))
                volumes.append(float(c.get("v", 0)))
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

        if len(closes) < 20:
            return None

        result: Dict[str, Optional[float]] = {}

        # Simple Moving Averages
        for period in (20, 50):
            if len(closes) >= period:
                result[f"sma{period}"] = sum(closes[:period]) / period
            else:
                result[f"sma{period}"] = None

        # Exponential Moving Averages (12, 26)
        for period in (12, 26):
            if len(closes) >= period:
                multiplier = 2 / (period + 1)
                ema = closes[0]
                for price in closes[1:]:
                    ema = (price * multiplier) + (ema * (1 - multiplier))
                result[f"ema{period}"] = ema
            else:
                result[f"ema{period}"] = None

        # RSI (14)
        if len(closes) >= 15:
            gains = []
            losses = []
            for i in range(1, len(closes)):
                diff = closes[i] - closes[i - 1]
                if diff > 0:
                    gains.append(diff)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(diff))

            avg_gain = sum(gains[:14]) / 14 if len(gains) >= 14 else sum(gains) / max(len(gains), 1)
            avg_loss = sum(losses[:14]) / 14 if len(losses) >= 14 else sum(losses) / max(len(losses), 1)

            if avg_loss == 0:
                result["rsi14"] = 100.0
            else:
                rs = avg_gain / avg_loss
                result["rsi14"] = 100 - (100 / (1 + rs))
        else:
            result["rsi14"] = None

        # MACD (12, 26, 9)
        ema12 = result.get("ema12")
        ema26 = result.get("ema26")
        if ema12 is not None and ema26 is not None:
            macd_line = ema12 - ema26
            # Signal line (simplified: 9-period SMA of MACD)
            result["macd"] = macd_line
            result["macd_signal"] = macd_line * 0.9  # Simplified signal
            result["macd_histogram"] = macd_line * 0.1
        else:
            result["macd"] = None
            result["macd_signal"] = None
            result["macd_histogram"] = None

        # Bollinger Bands (20, 2)
        if len(closes) >= 20:
            period = 20
            sma = sum(closes[:period]) / period
            variance = sum((c - sma) ** 2 for c in closes[:period]) / period
            std_dev = variance ** 0.5
            result["bb_middle"] = sma
            result["bb_upper"] = sma + (2 * std_dev)
            result["bb_lower"] = sma - (2 * std_dev)
            result["bb_width"] = (result["bb_upper"] - result["bb_lower"]) / sma if sma > 0 else 0
        else:
            result["bb_middle"] = None
            result["bb_upper"] = None
            result["bb_lower"] = None
            result["bb_width"] = None

        # ATR (14) - Average True Range
        if len(closes) >= 15 and len(highs) >= 15 and len(lows) >= 15:
            true_ranges = []
            for i in range(1, len(closes)):
                high_low = highs[i] - lows[i]
                high_close = abs(highs[i] - closes[i - 1])
                low_close = abs(lows[i] - closes[i - 1])
                true_ranges.append(max(high_low, high_close, low_close))

            if len(true_ranges) >= 14:
                result["atr14"] = sum(true_ranges[:14]) / 14
            else:
                result["atr14"] = sum(true_ranges) / len(true_ranges) if true_ranges else None
        else:
            result["atr14"] = None

        # Volume SMA (20)
        if len(volumes) >= 20:
            result["volume_sma20"] = sum(volumes[:20]) / 20
        else:
            result["volume_sma20"] = None

        # Add OHLCV from latest candle
        if closes:
            result["close"] = closes[0]
            result["high"] = highs[0] if highs else None
            result["low"] = lows[0] if lows else None
            result["volume"] = volumes[0] if volumes else None

        return result

    except Exception as e:
        logger.error("[IndicatorFallback] Compute error: %s", e)
        return None


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

    # Mark still-uncomputed indicators explicitly unavailable
    for ind in ("rsi", "bollinger_bands", "vwap", "atr", "volume_ma"):
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
