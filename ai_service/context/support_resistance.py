"""Support and resistance calculator for AI analysis context.

Calculates support and resistance levels from a candle array using:
- Recent swing highs/lows (price structure)
- Local pivots (3-candle fractals)
- Highest high / lowest low in lookback window

Used by the technical_analysis expert to enrich chart context.
"""
from __future__ import annotations

from typing import Any, Dict, List


def calculate_support_resistance(candles: List[Dict[str, Any]], lookback: int = 50) -> Dict[str, Any]:
    """Calculate support and resistance levels.

    Args:
        candles: List of candle dicts with keys: high, low, close.
                 Sorted by time ascending.
        lookback: Number of candles to consider.

    Returns:
        Dict with support_levels, resistance_levels, current_price, nearest support/resistance.
    """
    if not candles:
        return {
            "support_levels": [],
            "resistance_levels": [],
            "current_price": None,
            "nearest_support": None,
            "nearest_resistance": None,
        }

    # Use recent candles
    recent = candles[-lookback:] if len(candles) > lookback else candles
    current_price = recent[-1]["close"]

    swing_lows = []
    swing_highs = []

    # ── Detect local pivots (3-candle fractals) ──
    for i in range(1, len(recent) - 1):
        prev = recent[i - 1]
        curr = recent[i]
        nxt = recent[i + 1]

        # Swing low: current low < prev low and < next low
        if curr["low"] < prev["low"] and curr["low"] < nxt["low"]:
            swing_lows.append(curr["low"])

        # Swing high: current high > prev high and > next high
        if curr["high"] > prev["high"] and curr["high"] > nxt["high"]:
            swing_highs.append(curr["high"])

    # Add absolute extremes
    swing_lows.append(min(c["low"] for c in recent))
    swing_highs.append(max(c["high"] for c in recent))

    # Deduplicate nearby levels (within 0.5%)
    def deduplicate(levels: List[float], tolerance_pct: float = 0.5) -> List[float]:
        if not levels:
            return []
        levels.sort()
        deduped = [levels[0]]
        for lvl in levels[1:]:
            if abs(lvl - deduped[-1]) / deduped[-1] * 100 > tolerance_pct:
                deduped.append(lvl)
        return deduped

    support_levels = deduplicate(swing_lows)
    resistance_levels = deduplicate(swing_highs)

    # Nearest levels
    supports_below = [s for s in support_levels if s < current_price]
    resistances_above = [r for r in resistance_levels if r > current_price]

    nearest_support = max(supports_below) if supports_below else None
    nearest_resistance = min(resistances_above) if resistances_above else None

    return {
        "support_levels": support_levels[-5:],   # keep most recent/strongest
        "resistance_levels": resistance_levels[:5],
        "current_price": current_price,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "range_pct": round((nearest_resistance - nearest_support) / current_price * 100, 2)
                    if nearest_support and nearest_resistance else None,
    }


def summarize_levels(sr_data: Dict[str, Any]) -> str:
    """Summarize support/resistance levels in plain text."""
    supports = sr_data.get("support_levels", [])
    resistances = sr_data.get("resistance_levels", [])
    current = sr_data.get("current_price")
    nearest_support = sr_data.get("nearest_support")
    nearest_resistance = sr_data.get("nearest_resistance")

    parts = []
    if current is not None:
        parts.append(f"Current price: {current:.2f}")
    if nearest_support:
        parts.append(f"Nearest support: {nearest_support:.2f}")
    if nearest_resistance:
        parts.append(f"Nearest resistance: {nearest_resistance:.2f}")
    if supports:
        parts.append(f"Support levels: {[round(s, 2) for s in supports]}")
    if resistances:
        parts.append(f"Resistance levels: {[round(r, 2) for r in resistances]}")
    return ", ".join(parts)
