"""
Order book API — real-time bid/ask depth data with source/freshness metadata.
"""

from __future__ import annotations

import json
import time

import httpx
from fastapi import APIRouter, HTTPException, Query

from backend.core.database import get_redis
from backend.core.redis_sentinel import get_redis_master
from backend.models.common import DataFreshness

router = APIRouter(prefix="/api", tags=["orderbook"])

_BINANCE_CLIENT = httpx.AsyncClient(timeout=3.0)


async def _fetch_binance_orderbook(symbol: str, limit: int = 50) -> dict | None:
    """Fetch order book from Binance REST API as async fallback."""
    url = "https://api.binance.com/api/v3/depth"
    try:
        resp = await _BINANCE_CLIENT.get(url, params={"symbol": symbol, "limit": limit})
        resp.raise_for_status()
        payload = resp.json()
        bids = [[float(p), float(q)] for p, q in payload.get("bids", [])]
        asks = [[float(p), float(q)] for p, q in payload.get("asks", [])]
        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        return {
            "bids": bids,
            "asks": asks,
            "spread": round(best_ask - best_bid, 8) if (best_bid and best_ask) else 0.0,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "event_time": int(time.time() * 1000),
        }
    except (httpx.HTTPError, ValueError, KeyError):
        return None


@router.get("/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    exchange: str = Query("binance", description="Exchange name"),
):
    symbol_u = symbol.upper()
    r = await get_redis()
    now_ms = int(time.time() * 1000)
    source = "unavailable"
    found_exchange = None
    is_synthetic = False

    # Try requested exchange first, then fallback chain
    data = None
    for ex in (exchange, "binance", "okx"):
        data = await r.hgetall(f"orderbook:{ex}:{symbol_u}")  # type: ignore
        if data:
            source = "redis"
            found_exchange = ex
            break

    if not data:
        # Try old format
        data = await r.hgetall(f"orderbook:{symbol_u}")  # type: ignore
        if data:
            source = "redis"
            found_exchange = "unknown"

    if not data:
        # Try ticker-derived synthetic book
        ticker = None
        for ex in (exchange, "binance", "okx"):
            ticker = await r.hgetall(f"ticker:latest:{ex}:{symbol_u}")  # type: ignore
            if ticker:
                found_exchange = ex
                break

        if not ticker:
            ticker = await r.hgetall(f"ticker:latest:{symbol_u}")  # type: ignore
            found_exchange = "unknown"

        if ticker:
            bid = float(ticker.get("bid", 0) or 0)
            ask = float(ticker.get("ask", 0) or 0)
            event_time = int(float(ticker.get("event_time", 0) or 0))
            if bid > 0 and ask > 0:
                freshness_seconds = (now_ms - event_time) / 1000.0 if event_time else None
                return {
                    "symbol": symbol_u,
                    "bids": [[bid, 0.0]],
                    "asks": [[ask, 0.0]],
                    "spread": round(ask - bid, 8),
                    "best_bid": bid,
                    "best_ask": ask,
                    "event_time": event_time,
                    "metadata": {
                        "source": "ticker_derived",
                        "exchange": found_exchange,
                        "is_synthetic": True,
                        "freshness": DataFreshness(
                            source="ticker_derived",
                            exchange=found_exchange,
                            event_time=event_time,
                            freshness_seconds=freshness_seconds,
                            is_stale=freshness_seconds is not None and freshness_seconds > 30,
                            is_fallback=True,
                            warnings=[
                                "Order book derived from ticker bid/ask only — no depth levels available.",
                            ],
                        ).model_dump(),
                    },
                }

        # Try Binance REST as last resort
        fallback = await _fetch_binance_orderbook(symbol_u)
        if not fallback:
            raise HTTPException(404, f"No order book for {symbol}")

        # Warm cache for clients that poll frequently
        r_master = await get_redis_master()
        await r_master.hset(  # type: ignore
            f"orderbook:binance:{symbol_u}",
            mapping={
                "bids": json.dumps(fallback["bids"]),
                "asks": json.dumps(fallback["asks"]),
                "spread": fallback["spread"],
                "best_bid": fallback["best_bid"],
                "best_ask": fallback["best_ask"],
                "event_time": fallback["event_time"],
            },
        )
        await r_master.expire(f"orderbook:binance:{symbol_u}", 30)  # type: ignore

        freshness_seconds = (now_ms - fallback["event_time"]) / 1000.0
        return {
            "symbol": symbol_u,
            **fallback,
            "metadata": {
                "source": "binance_rest",
                "exchange": "binance",
                "is_synthetic": False,
                "freshness": DataFreshness(
                    source="binance_rest",
                    exchange="binance",
                    event_time=fallback["event_time"],
                    freshness_seconds=freshness_seconds,
                    is_stale=False,
                    is_fallback=True,
                    warnings=["Fetched from Binance REST API as fallback — not from live WebSocket stream."],
                ).model_dump(),
            },
        }

    # Parse Redis data
    event_time = int(float(data.get("event_time", 0)))
    freshness_seconds = (now_ms - event_time) / 1000.0 if event_time else None

    return {
        "symbol": symbol_u,
        "bids": json.loads(data.get("bids", "[]")),
        "asks": json.loads(data.get("asks", "[]")),
        "spread": float(data.get("spread", 0)),
        "best_bid": float(data.get("best_bid", 0)),
        "best_ask": float(data.get("best_ask", 0)),
        "event_time": event_time,
        "metadata": {
            "source": source,
            "exchange": found_exchange,
            "is_synthetic": False,
            "freshness": DataFreshness(
                source=source,
                exchange=found_exchange,
                event_time=event_time,
                freshness_seconds=freshness_seconds,
                is_stale=freshness_seconds is not None and freshness_seconds > 60,
                is_fallback=False,
            ).model_dump(),
        },
    }


@router.get("/orderbook/{symbol}/summary")
async def get_orderbook_summary(
    symbol: str,
    exchange: str = Query("binance", description="Exchange name"),
):
    """Compact order book summary for AI context."""
    # Reuse main endpoint and extract summary
    result = await get_orderbook(symbol, exchange)

    bids = result.get("bids", [])
    if not isinstance(bids, list):
        bids = []
    asks = result.get("asks", [])
    if not isinstance(asks, list):
        asks = []

    bid_depth = sum((float(level[1]) for level in bids)) if bids else 0.0
    ask_depth = sum((float(level[1]) for level in asks)) if asks else 0.0
    total_depth = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0.0

    # Top liquidity levels
    top_bids = bids[:5] if bids else []
    top_asks = asks[:5] if asks else []

    metadata = result.get("metadata", {})
    exchange_val = metadata.get("exchange") if isinstance(metadata, dict) else None

    return {
        "symbol": result.get("symbol", symbol.upper()),
        "exchange": exchange_val,
        "best_bid": result.get("best_bid"),
        "best_ask": result.get("best_ask"),
        "spread": result.get("spread"),
        "bid_depth": round(bid_depth, 4),
        "ask_depth": round(ask_depth, 4),
        "imbalance": round(imbalance, 4),
        "top_bid_levels": top_bids,
        "top_ask_levels": top_asks,
        "metadata": result.get("metadata"),
    }
