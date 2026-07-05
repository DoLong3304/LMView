"""
Data mappers for Binance WebSocket and REST API responses.

Converts raw Binance JSON (single-letter keys) to canonical records
with descriptive field names matching the Avro schemas.
"""

import json
import time


def map_ticker(raw: dict) -> dict:
    """Map a raw ``!ticker@arr`` item to a canonical ticker record."""
    return {
        "event_time":           int(raw["E"]),
        "symbol":               str(raw["s"]),
        "exchange":             "binance",
        "close":                float(raw.get("c", 0)),
        "bid":                  float(raw.get("b", 0)),
        "ask":                  float(raw.get("a", 0)),
        "h24_open":             float(raw.get("o", 0)),
        "h24_high":             float(raw.get("h", 0)),
        "h24_low":              float(raw.get("l", 0)),
        "h24_volume":           float(raw.get("v", 0)),
        "h24_quote_volume":     float(raw.get("q", 0)),
        "h24_price_change":     float(raw.get("p", 0)),
        "h24_price_change_pct": float(raw.get("P", 0)),
        "h24_trade_count":      int(raw.get("n", 0)),
    }


def map_ticker_rest(raw: dict) -> dict:
    """Map a Binance REST ``/api/v3/ticker/24hr`` response to a canonical ticker record.

    REST API uses full field names (``symbol``, ``lastPrice``, ``bidPrice``)
    instead of the single-letter keys (``s``, ``c``, ``b``) used by the
    WebSocket ``!ticker@arr`` stream. This mapper bridges the gap.
    """
    return {
        "event_time":           int(raw.get("closeTime", 0)),
        "symbol":               str(raw.get("symbol", "")),
        "exchange":             "binance",
        "close":                float(raw.get("lastPrice", 0)),
        "bid":                  float(raw.get("bidPrice", raw.get("bid", 0))),
        "ask":                  float(raw.get("askPrice", raw.get("ask", 0))),
        "h24_open":             float(raw.get("openPrice", 0)),
        "h24_high":             float(raw.get("highPrice", 0)),
        "h24_low":              float(raw.get("lowPrice", 0)),
        "h24_volume":           float(raw.get("volume", 0)),
        "h24_quote_volume":     float(raw.get("quoteVolume", 0)),
        "h24_price_change":     float(raw.get("priceChange", 0)),
        "h24_price_change_pct": float(raw.get("priceChangePercent", 0)),
        "h24_trade_count":      int(raw.get("count", 0)),
    }


def map_agg_trade(raw: dict) -> dict:
    """Map a raw ``@aggTrade`` event to a canonical trade record."""
    return {
        "event_time":     int(raw["E"]),
        "symbol":         str(raw["s"]),
        "exchange":       "binance",
        "agg_trade_id":   int(raw["a"]),
        "price":          float(raw["p"]),
        "quantity":       float(raw["q"]),
        "trade_time":     int(raw["T"]),
        "is_buyer_maker": bool(raw["m"]),
    }


def map_kline(raw: dict) -> dict:
    """Map a raw ``@kline`` event to a canonical kline record."""
    k = raw["k"]
    return {
        "event_time":   int(raw["E"]),
        "symbol":       str(raw["s"]),
        "exchange":     "binance",
        "kline_start":  int(k["t"]),
        "kline_close":  int(k["T"]),
        "interval":     str(k["i"]),
        "open":         float(k["o"]),
        "high":         float(k["h"]),
        "low":          float(k["l"]),
        "close":        float(k["c"]),
        "volume":       float(k["v"]),
        "quote_volume": float(k["q"]),
        "trade_count":  int(k["n"]),
        "is_closed":    bool(k["x"]),
    }


def map_depth(raw: dict) -> dict:
    """Map a raw partial depth snapshot to a canonical depth record.

    bids/asks are JSON-encoded strings for Avro compatibility.
    """
    return {
        "event_time":     int(raw.get("E", int(time.time() * 1000))),
        "symbol":         str(raw.get("s", "")).upper(),
        "exchange":       "binance",
        "last_update_id": int(raw.get("lastUpdateId", raw.get("u", 0))),
        "bids":           json.dumps([[float(p), float(q)] for p, q in (raw.get("bids") or raw.get("b") or [])]),
        "asks":           json.dumps([[float(p), float(q)] for p, q in (raw.get("asks") or raw.get("a") or [])]),
    }
