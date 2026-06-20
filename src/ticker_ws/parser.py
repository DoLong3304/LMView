"""Map Binance @ticker payload → Redis hash fields (24 fields)."""

from __future__ import annotations

from typing import Dict


# Fields we always write to Redis. Default ``""`` if Binance omits any.
REDIS_FIELDS = (
    "price",          # c: last price (close)
    "bid",            # b: best bid price
    "ask",            # a: best ask price
    "bid_qty",        # B: best bid quantity
    "ask_qty",        # A: best ask quantity
    "volume",         # v: total traded base asset volume (24h)
    "quote_volume",   # q: total traded quote asset volume (24h)
    "change_pct",     # P: price change percent
    "change_abs",     # p: price change absolute
    "weighted_avg",   # w: weighted average price
    "open_24h",       # o: open price (24h)
    "high_24h",       # h: high price (24h)
    "low_24h",        # l: low price (24h)
    "last_qty",       # Q: last quantity
    "open_time",      # O: statistics open time (ms)
    "close_time",     # C: statistics close time (ms)
    "first_trade_id", # F: first trade ID
    "last_trade_id",  # L: last trade ID
    "num_trades",     # n: total number of trades
    "event_time",     # E: event time (ms)
)


def parse_ticker(payload: Dict) -> Dict[str, str] | None:
    """Convert Binance @ticker payload into Redis hash mapping.

    Returns ``None`` if payload is invalid or symbol missing.
    """
    sym = payload.get("s")
    if not sym:
        return None

    out: Dict[str, str] = {
        "price":          str(payload.get("c", "")),
        "bid":            str(payload.get("b", "")),
        "ask":            str(payload.get("a", "")),
        "bid_qty":        str(payload.get("B", "")),
        "ask_qty":        str(payload.get("A", "")),
        "volume":         str(payload.get("v", "")),
        "quote_volume":   str(payload.get("q", "")),
        "change_pct":     str(payload.get("P", "")),
        "change_abs":     str(payload.get("p", "")),
        "weighted_avg":   str(payload.get("w", "")),
        "open_24h":       str(payload.get("o", "")),
        "high_24h":       str(payload.get("h", "")),
        "low_24h":        str(payload.get("l", "")),
        "last_qty":       str(payload.get("Q", "")),
        "open_time":      str(payload.get("O", "")),
        "close_time":     str(payload.get("C", "")),
        "first_trade_id": str(payload.get("F", "")),
        "last_trade_id":  str(payload.get("L", "")),
        "num_trades":     str(payload.get("n", "")),
        "event_time":     str(payload.get("E", "")),
        "exchange":       "binance",
    }

    # Drop any field whose source value is None (defensive against
    # Binance future schema changes)
    return {k: v for k, v in out.items() if v != ""}


def redis_key(exchange: str, symbol: str) -> str:
    """Build Redis key for the ticker hash."""
    return f"ticker:latest:{exchange.lower()}:{symbol}"