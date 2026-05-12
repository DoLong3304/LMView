from fastapi import APIRouter, HTTPException, Query

from backend.core.database import get_redis

router = APIRouter(prefix="/api", tags=["ticker"])


@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange: str = Query(None, description="Filter by exchange (binance, okx) or aggregate if not specified")
):
    """Get ticker data for a symbol.

    - If exchange is specified: returns data from that exchange only
    - If exchange is None: returns aggregated mid-price from all exchanges
    """
    r = await get_redis()
    symbol_upper = symbol.upper()

    if exchange:
        # Single exchange mode
        exchange_lower = exchange.lower()
        data = await r.hgetall(f"ticker:latest:{exchange_lower}:{symbol_upper}")
        if not data:
            raise HTTPException(404, f"No ticker data for {symbol} on {exchange}")
        return {
            "symbol": symbol_upper,
            "exchange": exchange_lower,
            "price": float(data.get("price", 0)),
            "change24h": float(data.get("change24h", 0)),
            "bid": float(data.get("bid", 0)),
            "ask": float(data.get("ask", 0)),
            "volume": float(data.get("volume", 0)),
            "event_time": int(float(data.get("event_time", 0))),
        }
    else:
        # Multi-exchange aggregation mode (mid-price)
        binance_data = await r.hgetall(f"ticker:latest:binance:{symbol_upper}")
        okx_data = await r.hgetall(f"ticker:latest:okx:{symbol_upper}")

        if not binance_data and not okx_data:
            raise HTTPException(404, f"No ticker data for {symbol}")

        # Calculate mid-price from available exchanges
        prices = []
        volumes = []
        event_times = []

        if binance_data:
            binance_price = binance_data.get("price")
            if binance_price:
                prices.append(float(binance_price))
            binance_volume = binance_data.get("volume")
            if binance_volume:
                volumes.append(float(binance_volume))
            binance_event_time = binance_data.get("event_time")
            if binance_event_time:
                event_times.append(int(float(binance_event_time)))

        if okx_data:
            okx_price = okx_data.get("price")
            if okx_price:
                prices.append(float(okx_price))
            okx_volume = okx_data.get("volume")
            if okx_volume:
                volumes.append(float(okx_volume))
            okx_event_time = okx_data.get("event_time")
            if okx_event_time:
                event_times.append(int(float(okx_event_time)))

        mid_price = sum(prices) / len(prices) if prices else 0
        total_volume = sum(volumes)
        latest_event_time = max(event_times) if event_times else 0

        # Use binance data for other fields (bid, ask, change24h) as primary
        primary_data = binance_data if binance_data else okx_data

        return {
            "symbol": symbol_upper,
            "exchange": "aggregated",
            "price": mid_price,
            "change24h": float(primary_data.get("change24h", 0)),
            "bid": float(primary_data.get("bid", 0)),
            "ask": float(primary_data.get("ask", 0)),
            "volume": total_volume,
            "event_time": latest_event_time,
            "sources": {
                "binance": float(binance_data.get("price", 0)) if binance_data else None,
                "okx": float(okx_data.get("price", 0)) if okx_data else None,
            }
        }


@router.get("/ticker")
async def get_all_tickers(
    exchange: str = Query(None, description="Filter by exchange (binance, okx)")
):
    """Get all ticker data.

    - If exchange is specified: returns data from that exchange only
    - If exchange is None: returns aggregated data from all exchanges
    """
    r = await get_redis()
    result = []

    if exchange:
        # Single exchange mode
        exchange_lower = exchange.lower()
        pattern = f"ticker:latest:{exchange_lower}:*"
        async for key in r.scan_iter(match=pattern, count=200):
            symbol = key.split(":", 3)[-1]
            data = await r.hgetall(key)
            if data:
                result.append({
                    "symbol": symbol,
                    "exchange": exchange_lower,
                    "price": float(data.get("price", 0)),
                    "change24h": float(data.get("change24h", 0)),
                    "bid": float(data.get("bid", 0)),
                    "ask": float(data.get("ask", 0)),
                    "volume": float(data.get("volume", 0)),
                    "event_time": int(float(data.get("event_time", 0))),
                })
    else:
        # Multi-exchange aggregation mode
        symbols_seen = set()
        all_data = {}

        # Collect data from all exchanges
        async for key in r.scan_iter(match="ticker:latest:*:*", count=200):
            parts = key.split(":", 3)
            if len(parts) == 4:
                exchange_name = parts[2]
                symbol = parts[3]
                data = await r.hgetall(key)
                if data:
                    if symbol not in all_data:
                        all_data[symbol] = {}
                    all_data[symbol][exchange_name] = data
                    symbols_seen.add(symbol)

        # Aggregate per symbol
        for symbol in sorted(symbols_seen):
            exchanges_data = all_data.get(symbol, {})
            prices = []
            volumes = []
            event_times = []

            for exchange_name, data in exchanges_data.items():
                price = data.get("price")
                if price:
                    prices.append(float(price))
                volume = data.get("volume")
                if volume:
                    volumes.append(float(volume))
                event_time = data.get("event_time")
                if event_time:
                    event_times.append(int(float(event_time)))

            mid_price = sum(prices) / len(prices) if prices else 0
            total_volume = sum(volumes)
            latest_event_time = max(event_times) if event_times else 0

            # Use first available exchange for other fields
            primary_data = list(exchanges_data.values())[0] if exchanges_data else {}

            result.append({
                "symbol": symbol,
                "exchange": "aggregated",
                "price": mid_price,
                "change24h": float(primary_data.get("change24h", 0)),
                "bid": float(primary_data.get("bid", 0)),
                "ask": float(primary_data.get("ask", 0)),
                "volume": total_volume,
                "event_time": latest_event_time,
            })

    result.sort(key=lambda t: t["symbol"])
    return result
