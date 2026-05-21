from fastapi import APIRouter, HTTPException, Query

from backend.core.database import get_redis

router = APIRouter(prefix="/api", tags=["trades"])


@router.get("/trades/{symbol}")
async def get_trades(symbol: str, limit: int = Query(50, ge=1, le=200)):
    """
    Recent price ticks derived from the ticker history sorted set in KeyDB.

    Note: These are ticker-level price movements, not individual exchange trades.
    The Flink pipeline stores ``{price}:{volume}`` in ``ticker:history:{exchange}:{symbol}``
    with score = event_time (ms).
    """
    r = await get_redis()
    # Try Binance first
    key = f"ticker:history:binance:{symbol.upper()}"
    raw = await r.zrevrange(key, 0, limit - 1, withscores=True)
    if not raw:
        # Fallback to OKX
        key = f"ticker:history:okx:{symbol.upper()}"
        raw = await r.zrevrange(key, 0, limit - 1, withscores=True)
    if not raw:
        # Fallback to old format
        key = f"ticker:history:{symbol.upper()}"
        raw = await r.zrevrange(key, 0, limit - 1, withscores=True)
    if not raw:
        raise HTTPException(404, f"No trade data for {symbol}")
    trades = []
    prev_price = None
    for member, score in raw:
        parts = str(member).split(":")
        price = float(parts[0])
        volume = float(parts[1]) if len(parts) > 1 else 0
        side = "buy" if prev_price is None or price >= prev_price else "sell"
        trades.append({
            "time": int(score),
            "price": price,
            "volume": volume,
            "side": side,
        })
        prev_price = price
    trades.reverse()  # chronological order
    return trades
