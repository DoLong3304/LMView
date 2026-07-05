"""Map Binance @kline_1s payload → Redis sorted-set candle dict.

Binance kline payload format (from WebSocket @kline_1s):
```json
{
  "e": "kline",
  "E": 1735689600000,
  "s": "BTCUSDT",
  "k": {
    "t": 1735689600000,   // Kline start time
    "T": 1735689601000,   // Kline close time
    "s": "BTCUSDT",       // Symbol
    "i": "1s",            // Interval
    "f": 100,             // First trade ID
    "L": 200,             // Last trade ID
    "o": "50000.00",      // Open
    "c": "50001.00",      // Close
    "h": "50002.00",      // High
    "l": "49999.00",      // Low
    "v": "1.5",           // Volume
    "n": 10,              // Number of trades
    "x": false,           // Is this kline closed?
    "q": "75000.00",      // Quote volume
    "V": "0.8",           // Taker buy base volume
    "Q": "40000.00",      // Taker buy quote volume
    "B": "0"              // Ignore
  }
}
```

Redis output:
- Key: `candle:1s:binance:{symbol}`
- ZADD member: `{"t": <open_ms>, "o": <open>, "h": <high>, "l": <low>, "c": <close>,
                  "v": <volume>, "qv": <quote_volume>, "n": <trade_count>, "x": <is_closed>}`
- Score: `<open_ms>` (for range queries)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def parse_kline(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert Binance @kline_1s WS payload → candle dict for Redis.

    Returns ``None`` if payload is invalid or symbol missing.
    Returns dict with keys: symbol, exchange, interval, kline_start, open,
    high, low, close, volume, quote_volume, trade_count, is_closed,
    candle_json, history_key.
    """
    k = payload.get("k")
    if not isinstance(k, dict):
        return None

    symbol = payload.get("s", "")
    if not symbol or not symbol.endswith("USDT"):
        return None

    kline_start = int(k.get("t", 0))
    if kline_start == 0:
        return None

    interval = k.get("i", "1s")
    if interval != "1s":
        return None

    o = float(k.get("o", 0))
    h = float(k.get("h", 0))
    l = float(k.get("l", 0))
    c = float(k.get("c", 0))
    v = float(k.get("v", 0))
    qv = float(k.get("q", 0))
    n = int(k.get("n", 0))
    x = bool(k.get("x", False))

    candle_json = json.dumps(
        {"t": kline_start, "o": o, "h": h, "l": l, "c": c,
         "v": v, "qv": qv, "n": n, "x": x},
        separators=(",", ":"),
    )

    return {
        "symbol": symbol,
        "exchange": "binance",
        "interval": interval,
        "kline_start": kline_start,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "quote_volume": qv,
        "trade_count": n,
        "is_closed": x,
        "candle_json": candle_json,
        "history_key": f"candle:1s:binance:{symbol}",
    }


def redis_key(exchange: str, symbol: str) -> str:
    """Build Redis key for the 1s candle sorted set."""
    return f"candle:1s:{exchange.lower()}:{symbol}"
