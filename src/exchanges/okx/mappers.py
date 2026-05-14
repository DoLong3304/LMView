"""
Data mappers for OKX WebSocket and REST API responses.

Converts raw OKX JSON to canonical records matching the Avro schemas.
OKX uses different field names (instId instead of symbol, etc.).
"""

import json
import time


def normalize_symbol(inst_id: str) -> str:
    """Convert OKX instId (BTC-USDT) to canonical symbol (BTCUSDT)."""
    return inst_id.replace("-", "")


def map_ticker(raw: dict) -> dict:
    """Map a raw OKX ticker to canonical ticker record.

    OKX ticker format:
    {
        "instType": "SPOT",
        "instId": "BTC-USDT",
        "last": "50000",
        "lastSz": "0.01",
        "askPx": "50001",
        "askSz": "1.5",
        "bidPx": "49999",
        "bidSz": "2.0",
        "open24h": "49500",
        "high24h": "50500",
        "low24h": "49000",
        "volCcy24h": "1000000",
        "vol24h": "20",
        "ts": "1609459200000"
    }
    """
    symbol = normalize_symbol(raw.get("instId", ""))
    last = float(raw.get("last", 0))
    open_24h = float(raw.get("open24h", 0))

    # Calculate 24h price change
    price_change = last - open_24h if open_24h > 0 else 0
    price_change_pct = (price_change / open_24h * 100) if open_24h > 0 else 0

    return {
        "event_time":           int(raw.get("ts", int(time.time() * 1000))),
        "symbol":               symbol,
        "exchange":             "okx",
        "close":                last,
        "bid":                  float(raw.get("bidPx", 0)),
        "ask":                  float(raw.get("askPx", 0)),
        "h24_open":             open_24h,
        "h24_high":             float(raw.get("high24h", 0)),
        "h24_low":              float(raw.get("low24h", 0)),
        "h24_volume":           float(raw.get("vol24h", 0)),
        "h24_quote_volume":     float(raw.get("volCcy24h", 0)),
        "h24_price_change":     price_change,
        "h24_price_change_pct": price_change_pct,
        "h24_trade_count":      0,  # OKX doesn't provide trade count in ticker
    }


def map_agg_trade(raw: dict) -> dict:
    """Map a raw OKX trade to canonical trade record.

    OKX trade format:
    {
        "instId": "BTC-USDT",
        "tradeId": "12345",
        "px": "50000",
        "sz": "0.01",
        "side": "buy",
        "ts": "1609459200000"
    }
    """
    return {
        "event_time":     int(raw.get("ts", int(time.time() * 1000))),
        "symbol":         normalize_symbol(raw.get("instId", "")),
        "exchange":       "okx",
        "agg_trade_id":   int(raw.get("tradeId", 0)),
        "price":          float(raw.get("px", 0)),
        "quantity":       float(raw.get("sz", 0)),
        "trade_time":     int(raw.get("ts", int(time.time() * 1000))),
        "is_buyer_maker": raw.get("side", "") == "sell",  # sell = maker is buyer
    }


def map_kline(raw: dict) -> dict:
    """Map a raw OKX kline to canonical kline record.

    OKX kline format (array):
    [
        "1609459200000",  # ts (open time)
        "50000",          # o (open)
        "50500",          # h (high)
        "49500",          # l (low)
        "50200",          # c (close)
        "100",            # vol (volume in base currency)
        "5000000",        # volCcy (volume in quote currency)
        "0"               # confirm (0=not closed, 1=closed)
    ]
    """
    if isinstance(raw, list) and len(raw) >= 8:
        kline_start = int(raw[0])
        # OKX uses 1s interval, so close time is start + 1000ms
        kline_close = kline_start + 1000

        return {
            "event_time":   int(time.time() * 1000),
            "symbol":       "",  # Will be set by caller
            "exchange":     "okx",
            "kline_start":  kline_start,
            "kline_close":  kline_close,
            "interval":     "1s",
            "open":         float(raw[1]),
            "high":         float(raw[2]),
            "low":          float(raw[3]),
            "close":        float(raw[4]),
            "volume":       float(raw[5]),
            "quote_volume": float(raw[6]),
            "trade_count":  0,  # OKX doesn't provide trade count
            "is_closed":    raw[7] == "1",
        }

    # Fallback for dict format
    return {
        "event_time":   int(raw.get("ts", int(time.time() * 1000))),
        "symbol":       normalize_symbol(raw.get("instId", "")),
        "exchange":     "okx",
        "kline_start":  int(raw.get("ts", 0)),
        "kline_close":  int(raw.get("ts", 0)) + 1000,
        "interval":     "1s",
        "open":         float(raw.get("o", 0)),
        "high":         float(raw.get("h", 0)),
        "low":          float(raw.get("l", 0)),
        "close":        float(raw.get("c", 0)),
        "volume":       float(raw.get("vol", 0)),
        "quote_volume": float(raw.get("volCcy", 0)),
        "trade_count":  0,
        "is_closed":    raw.get("confirm", "0") == "1",
    }


def map_depth(raw: dict) -> dict:
    """Map a raw OKX depth snapshot to canonical depth record.

    OKX depth format:
    {
        "asks": [["50001", "1.5", "0", "2"]],
        "bids": [["49999", "2.0", "0", "3"]],
        "ts": "1609459200000",
        "checksum": 123456
    }
    """
    return {
        "event_time":     int(raw.get("ts", int(time.time() * 1000))),
        "symbol":         "",  # Will be set by caller
        "exchange":       "okx",
        "last_update_id": int(raw.get("checksum", 0)),
        "bids":           json.dumps([[float(p), float(q)] for p, q, *_ in (raw.get("bids") or [])]),
        "asks":           json.dumps([[float(p), float(q)] for p, q, *_ in (raw.get("asks") or [])]),
    }
