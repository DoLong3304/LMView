from fastapi import APIRouter

from backend.core.database import get_redis

router = APIRouter(prefix="/api", tags=["symbols"])


@router.get("/symbols")
async def get_symbols():
    """
    List all active symbols by scanning ``ticker:latest:*`` keys in KeyDB.

    Supports both old format (ticker:latest:SYMBOL) and new format (ticker:latest:exchange:SYMBOL).

    Returns the shape expected by the React frontend:
    ``[{"symbol": "BTCUSDT", "name": "BTC / USDT", "type": "crypto"}]``
    """
    r = await get_redis()
    symbols = []
    seen = set()

    # Scan for both old format (ticker:latest:SYMBOL) and new format (ticker:latest:exchange:SYMBOL)
    async for key in r.scan_iter(match="ticker:latest:*", count=200):
        # New format: ticker:latest:exchange:symbol (e.g., ticker:latest:binance:BTCUSDT)
        # Old format: ticker:latest:symbol (e.g., ticker:latest:BTCUSDT)
        parts = key.split(":")
        if len(parts) == 3:
            # New format: ticker, latest, exchange:symbol or old: symbol
            second_part = parts[2]
            if ":" in second_part:
                # ticker:latest:binance:BTCUSDT format
                sym = second_part.split(":")[-1]
            else:
                # ticker:latest:SYMBOL (old format)
                sym = second_part
        elif len(parts) == 4:
            # ticker:latest:exchange:symbol format
            sym = parts[3]
        else:
            continue

        if sym in seen:
            continue
        seen.add(sym)

        if sym.endswith("USDT"):
            base = sym[:-4]
            name = f"{base} / USDT"
        elif sym.endswith("BTC"):
            base = sym[:-3]
            name = f"{base} / BTC"
        else:
            name = sym
        symbols.append({"symbol": sym, "name": name, "type": "crypto"})
    symbols.sort(key=lambda s: s["symbol"])
    return symbols
