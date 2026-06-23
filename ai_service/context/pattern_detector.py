"""Candlestick pattern detector for AI analysis context.

Detects common candlestick patterns from a candle array.
Patterns are identified by analyzing open/high/low/close relationships
across consecutive candles.

Used by the technical_analysis expert to enrich chart context.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def detect_patterns(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect candlestick patterns in a list of candles.

    Args:
        candles: List of candle dicts with keys: open, high, low, close, openTime.
                 Sorted by time ascending.

    Returns:
        List of detected patterns, each with: name, direction, index, confidence.
    """
    if not candles or len(candles) < 2:
        return []

    patterns: List[Dict[str, Any]] = []

    for i in range(1, len(candles)):
        candle = candles[i]
        prev = candles[i - 1]

        o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
        po, ph, pl, pc = prev["open"], prev["high"], prev["low"], prev["close"]

        body = abs(c - o)
        prev_body = abs(pc - po)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        total_range = h - l
        prev_total_range = ph - pl

        if total_range == 0:
            continue

        # ── Single-candle patterns ──

        # Doji: open ≈ close (very small body)
        if body / total_range < 0.05:
            patterns.append({
                "name": "doji",
                "direction": "neutral",
                "index": i,
                "confidence": 0.7,
                "description": "Open and close are nearly equal — indecision in the market.",
            })
            continue

        # Hammer: small body at top, long lower wick (≥2x body), little/no upper wick
        if body / total_range < 0.3 and lower_wick >= body * 2 and upper_wick <= body * 0.3:
            patterns.append({
                "name": "hammer",
                "direction": "bullish",
                "index": i,
                "confidence": 0.75,
                "description": "Long lower wick, small body at top — potential bullish reversal.",
            })
            continue

        # Shooting Star: small body at bottom, long upper wick (≥2x body), little/no lower wick
        if body / total_range < 0.3 and upper_wick >= body * 2 and lower_wick <= body * 0.3:
            patterns.append({
                "name": "shooting_star",
                "direction": "bearish",
                "index": i,
                "confidence": 0.75,
                "description": "Long upper wick, small body at bottom — potential bearish reversal.",
            })
            continue

        # Marubozu: very long body, no wicks
        if body / total_range > 0.9 and upper_wick < body * 0.05 and lower_wick < body * 0.05:
            direction = "bullish" if c > o else "bearish"
            patterns.append({
                "name": "marubozu",
                "direction": direction,
                "index": i,
                "confidence": 0.8,
                "description": f"Full-bodied {'green' if direction == 'bullish' else 'red'} candle — strong {'buying' if direction == 'bullish' else 'selling'} pressure.",
            })
            continue

        # ── Two-candle patterns ──

        # Engulfing: current body engulfs previous body
        if i >= 1:
            if abs(c - o) > abs(pc - po) and (
                (c > o and pc < po and c > po and o < pc) or
                (o > c and po < pc and o > pc and c < po)
            ):
                direction = "bullish" if c > o else "bearish"
                patterns.append({
                    "name": "engulfing",
                    "direction": direction,
                    "index": i,
                    "confidence": 0.8,
                    "description": f"{'Bullish' if direction == 'bullish' else 'Bearish'} engulfing — strong trend reversal signal.",
                })
                continue

        # Piercing Pattern (bullish) / Dark Cloud Cover (bearish)
        if i >= 1:
            if c > o and pc > po:  # both bullish
                # Piercing: current close > midpoint of previous body
                prev_mid = (ph + pl) / 2
                if po > pc and o < pl and c > prev_mid:
                    patterns.append({
                        "name": "piercing_pattern",
                        "direction": "bullish",
                        "index": i,
                        "confidence": 0.65,
                        "description": "Bullish piercing pattern — potential upward reversal.",
                    })
                    continue
            elif o > c and po > pc:  # both bearish
                prev_mid = (ph + pl) / 2
                if pc > po and c > ph and o < prev_mid:
                    patterns.append({
                        "name": "dark_cloud_cover",
                        "direction": "bearish",
                        "index": i,
                        "confidence": 0.65,
                        "description": "Dark cloud cover — potential downward reversal.",
                    })
                    continue

    return patterns


def detect_trend(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect broad trend direction and strength.

    Uses simple moving average comparison and sequential high/low analysis.
    """
    if not candles or len(candles) < 10:
        return {"direction": "neutral", "strength": 0.0}

    # Split into halves
    mid = len(candles) // 2
    first_half = candles[:mid]
    second_half = candles[mid:]

    avg_first = sum(c["close"] for c in first_half) / len(first_half)
    avg_second = sum(c["close"] for c in second_half) / len(second_half)

    pct_change = (avg_second - avg_first) / avg_first * 100

    # Count consecutive higher highs / lower lows
    higher_highs = 0
    lower_lows = 0
    for i in range(5, len(candles)):
        if candles[i]["high"] > candles[i - 1]["high"] and candles[i]["close"] > candles[i - 1]["close"]:
            higher_highs += 1
        elif candles[i]["low"] < candles[i - 1]["low"] and candles[i]["close"] < candles[i - 1]["close"]:
            lower_lows += 1

    if pct_change > 1.5 and higher_highs > lower_lows:
        return {"direction": "uptrend", "strength": min(1.0, abs(pct_change) / 10), "pct_change": round(pct_change, 2)}
    elif pct_change < -1.5 and lower_lows > higher_highs:
        return {"direction": "downtrend", "strength": min(1.0, abs(pct_change) / 10), "pct_change": round(pct_change, 2)}
    else:
        return {"direction": "neutral", "strength": 0.0, "pct_change": round(pct_change, 2)}
