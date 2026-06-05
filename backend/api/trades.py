"""
Trades API — recent price ticks from ticker history.

IMPORTANT: These are ticker-level price movements derived from the
ticker history sorted set, NOT true exchange aggregate trades.
The response metadata now clearly indicates this.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query

import json

from backend.core.database import get_redis
from backend.models.common import DataFreshness

router = APIRouter(prefix="/api", tags=["trades"])


@router.get("/trades/{symbol}")
async def get_trades(
    symbol: str,
    limit: int = Query(50, ge=1, le=200),
    exchange: str = Query("binance", description="Exchange name"),
):
    """
    Recent price ticks derived from the ticker history sorted set.

    Note: These are ticker-level price movements, not individual exchange trades.
    The Flink pipeline stores ``{price}:{volume}`` in ``ticker:history:{exchange}:{symbol}``
    with score = event_time (ms).
    """
    r = await get_redis()
    symbol_u = symbol.upper()
    source = "unavailable"
    found_exchange = None
    now_ms = int(time.time() * 1000)
    is_true_trade_tape = False
    warnings = []

    # Priority 1: Try real trade data from Flink trade cache (trade:latest)
    for ex in (exchange, "binance", "okx"):
        key = f"trade:latest:{ex}:{symbol_u}"
        raw = await r.zrevrange(key, 0, limit - 1, withscores=True)
        if raw:
            source = "redis"
            found_exchange = ex
            is_true_trade_tape = True
            break

    # Priority 2: Fallback to ticker-derived history
    if not raw:
        for ex in (exchange, "binance", "okx"):
            key = f"ticker:history:{ex}:{symbol_u}"
            raw = await r.zrevrange(key, 0, limit - 1, withscores=True)
            if raw:
                source = "redis"
                found_exchange = ex
                break

    if not raw:
        raise HTTPException(404, f"No trade data for {symbol}")

    trades = []
    prev_price = None
    latest_event_time = 0

    if is_true_trade_tape:
        # Parse trade JSON from trade cache
        for member, score in raw:
            trade = json.loads(member) if isinstance(member, str) else member
            price = float(trade.get("p", 0))
            volume = float(trade.get("q", 0))
            trade_time = int(trade.get("t", 0))
            is_buyer_maker = bool(trade.get("m", False))
            side = "sell" if is_buyer_maker else "buy"
            latest_event_time = max(latest_event_time, trade_time)
            trades.append({
                "time": trade_time,
                "price": price,
                "volume": volume,
                "side": side,
            })
        trades.reverse()  # chronological
    else:
        # Parse ticker-derived format: {price}:{volume}
        for member, score in raw:
            parts = str(member).split(":")
            price = float(parts[0])
            volume = float(parts[1]) if len(parts) > 1 else 0
            side = "buy" if prev_price is None or price >= prev_price else "sell"
            event_time = int(score)
            latest_event_time = max(latest_event_time, event_time)
            trades.append({
                "time": event_time,
                "price": price,
                "volume": volume,
                "side": side,
            })
            prev_price = price
        trades.reverse()

    freshness_seconds = (now_ms - latest_event_time) / 1000.0 if latest_event_time else None

    if not is_true_trade_tape:
        warnings = [
            "These are ticker-derived price movements, not true exchange trades.",
            "Side is inferred from price direction and may not reflect actual trade initiator.",
        ]

    return {
        "symbol": symbol_u,
        "trades": trades,
        "metadata": {
            "data_type": "exchange_trade" if is_true_trade_tape else "ticker_derived",
            "is_true_trade_tape": is_true_trade_tape,
            "source": source,
            "exchange": found_exchange,
            "tick_count": len(trades),
            "freshness": DataFreshness(
                source=source,
                exchange=found_exchange,
                event_time=latest_event_time if latest_event_time else None,
                freshness_seconds=freshness_seconds,
                is_stale=freshness_seconds is not None and freshness_seconds > 30,
                is_fallback=not is_true_trade_tape,
                warnings=warnings,
            ).model_dump(),
        },
    }


@router.get("/trades/{symbol}/summary")
async def get_trade_summary(
    symbol: str,
    exchange: str = Query("binance", description="Exchange name"),
):
    """Compact trade summary for AI context."""
    r = await get_redis()
    symbol_u = symbol.upper()
    now_ms = int(time.time() * 1000)

    raw = None
    found_exchange = exchange
    is_true_trade_tape = False

    # Priority 1: real trade data
    for ex in (exchange, "binance", "okx"):
        key = f"trade:latest:{ex}:{symbol_u}"
        raw = await r.zrevrange(key, 0, 49, withscores=True)
        if raw:
            found_exchange = ex
            is_true_trade_tape = True
            break

    # Priority 2: ticker-derived history
    if not raw:
        for ex in (exchange, "binance", "okx"):
            key = f"ticker:history:{ex}:{symbol_u}"
            raw = await r.zrevrange(key, 0, 49, withscores=True)
            if raw:
                found_exchange = ex
                break

    if not raw:
        return {
            "symbol": symbol_u,
            "latest_price": None,
            "tick_count": 0,
            "volume_sum": None,
            "inferred_direction": None,
            "data_type": "ticker_derived",
            "is_true_trade_tape": False,
            "warning": "No ticker data available",
        }

    prices = []
    volumes = []
    for member, score in raw:
        parts = str(member).split(":")
        prices.append(float(parts[0]))
        volumes.append(float(parts[1]) if len(parts) > 1 else 0)

    latest_price = prices[0] if prices else None
    oldest_price = prices[-1] if prices else None
    direction = None
    if latest_price is not None and oldest_price is not None:
        if latest_price > oldest_price:
            direction = "up"
        elif latest_price < oldest_price:
            direction = "down"
        else:
            direction = "flat"

    return {
        "symbol": symbol_u,
        "latest_price": latest_price,
        "tick_count": len(raw),
        "volume_sum": sum(volumes) if volumes else None,
        "inferred_direction": direction,
        "data_type": "ticker_derived",
        "is_true_trade_tape": False,
        "exchange": found_exchange,
        "warning": "Direction inferred from ticker price movement, not true trade tape.",
    }
