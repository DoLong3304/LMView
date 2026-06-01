"""
Indicator service — expanded indicator backend for Phase 0.

Provides indicator listing, latest values from Redis, and extensible
compute-from-candle-history for future expansion.
"""
from __future__ import annotations

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


async def get_indicator_snapshot(
    symbol: str,
    exchange: str = "binance",
) -> IndicatorSnapshot:
    """
    Get latest indicator values from Redis.

    Currently reads from ``indicator:latest:{symbol}`` which has
    SMA20, SMA50, EMA12, EMA26. Extended indicators (RSI, MACD, etc.)
    return as unavailable until the Flink/Spark pipeline computes them.
    """
    symbol_u = symbol.upper()
    r = await get_redis()

    data = await r.hgetall(f"indicator:latest:{symbol_u}")  # type: ignore

    now_ms = int(time.time() * 1000)
    indicators: Dict[str, Optional[float]] = {}
    source = "unavailable"
    timestamp = None

    if data:
        source = "redis"
        for field in ("sma20", "sma50", "ema12", "ema26"):
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

    # Mark extended indicators as unavailable
    for ind in ("rsi", "macd", "bollinger_bands", "vwap", "atr", "volume_ma"):
        indicators[ind] = None

    freshness_seconds = None
    if timestamp:
        freshness_seconds = (now_ms - timestamp) / 1000.0

    return IndicatorSnapshot(
        symbol=symbol_u,
        exchange=exchange,
        indicators=indicators,
        timestamp=timestamp,
        source=source,
        freshness=DataFreshness(
            source=source,
            exchange=exchange,
            event_time=timestamp,
            freshness_seconds=freshness_seconds,
            is_stale=freshness_seconds is not None and freshness_seconds > 120,
            is_fallback=source == "unavailable",
            warnings=["Extended indicators (RSI, MACD, BB, VWAP, ATR, Volume MA) not yet computed by pipeline"]
            if source != "unavailable" else ["No indicator data available"],
        ),
    )


async def get_indicator_summary(
    symbol: str,
    exchange: str = "binance",
) -> IndicatorSummary:
    """Get a compact indicator summary for AI context."""
    snapshot = await get_indicator_snapshot(symbol, exchange)

    available = [k for k, v in snapshot.indicators.items() if v is not None]

    return IndicatorSummary(
        symbol=snapshot.symbol,
        exchange=exchange,
        available=available,
        latest_values={k: v for k, v in snapshot.indicators.items() if v is not None},
        signals={},  # Phase 1+: compute signals from indicator values
        source=snapshot.source,
        freshness=snapshot.freshness,
    )
