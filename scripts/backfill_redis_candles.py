#!/usr/bin/env python3
"""
Historical Redis candle backfill via Binance REST API.

The ``refresh_redis_klines.py`` script only refreshes the most-recent ~500
candles (8.3 hours of 1m bars). This script paginates backward through the
Binance REST ``/api/v3/klines`` endpoint using ``endTime`` to fetch up to
``--days`` of historical 1m candles per symbol and writes them into the
canonical ``candle:1m:{exchange}:{symbol}`` sorted set.

Redis key shapes written (must match ``keydb_kline.py`` / ``DirectRedisWriter``):
    History (sorted set):
        ZADD candle:1m:{exchange}:{symbol} {open_time_ms} '{json}'
        EXPIRE candle:1m:{exchange}:{symbol} {ttl}
    Latest (hash):
        HSET candle:latest:{exchange}:{symbol} {open,high,...,interval,exchange}
        EXPIRE candle:latest:{exchange}:{symbol} {ttl}

ZADD with the same member+score is idempotent, so re-running this script is
safe — it fills gaps without overwriting newer live candles.

Usage:
    # Backfill 7 days of 1m candles for top 100 USDT symbols by 24h volume
    python scripts/backfill_redis_candles.py --days 7 --top 100

    # Backfill 30 days for specific symbols
    python scripts/backfill_redis_candles.py --days 30 --symbols BTCUSDT,ETHUSDT

    # Filter to symbols already partially in Redis (skip ones with no data)
    python scripts/backfill_redis_candles.py --days 7 --only-with-data

Env (read from container / host):
    REDIS_SENTINELS      comma-separated host:port list (preferred)
    REDIS_HOST           fallback single Redis host
    REDIS_PORT           fallback Redis port (default 6379)
    REDIS_MASTER_NAME    Sentinel master name (default mymaster)
    REDIS_PASSWORD       optional password
    KEYDB_1M_RETENTION_DAYS  Redis TTL in days (default 7)

Exit codes: 0 success, 1 partial failure, 2 total failure.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Iterable

import requests

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write("redis package not installed. pip install redis\n")
    raise

log = logging.getLogger("backfill_redis_candles")

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"
EXCHANGE = "binance"

# Match keydb_kline.py retention defaults so we don't shorten existing TTLs.
TTL_1M_SEC = max(int(os.environ.get("KEYDB_1M_RETENTION_DAYS", "7")), 1) * 86_400

# Stablecoin / fiat prefixes to skip (matches BinanceClient symbol filtering).
SYMBOL_BLACKLIST_PREFIXES = (
    "USDC", "FDUSD", "TUSDC", "USDP", "USD1", "EUR", "GBP", "TRY",
    "AEUR", "EURI", "USDS",
)

# Binance REST kline API max per-request limit.
BINANCE_KLINE_MAX = 1000


def get_redis_client() -> redis.Redis:
    """Build a Redis client using Sentinel if configured, else direct."""
    sentinels_env = os.environ.get("REDIS_SENTINELS", "").strip()
    master_name = os.environ.get("REDIS_MASTER_NAME", "mymaster")
    password = os.environ.get("REDIS_PASSWORD") or None

    if sentinels_env:
        sentinel_addrs = []
        for s in sentinels_env.split(","):
            s = s.strip()
            if not s:
                continue
            host, _, port = s.partition(":")
            sentinel_addrs.append((host, int(port or 26379)))
        if not sentinel_addrs:
            raise RuntimeError("REDIS_SENTINELS set but parsed empty")
        sentinel = redis.Sentinel(sentinel_addrs, socket_timeout=5, password=password)
        return sentinel.master_for(master_name, socket_timeout=5)

    host = os.environ.get("REDIS_HOST", "redis-master")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, socket_timeout=5, password=password)


def fetch_top_symbols(limit: int) -> list[str]:
    """Return top-N USDT symbols by 24h quote volume, filtering stablecoins."""
    resp = requests.get(BINANCE_24HR_URL, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    filtered = [
        (r["symbol"], float(r.get("quoteVolume", 0)))
        for r in rows
        if r["symbol"].endswith("USDT")
        and not r["symbol"].startswith(SYMBOL_BLACKLIST_PREFIXES)
    ]
    filtered.sort(key=lambda x: -x[1])
    return [s for s, _ in filtered[:limit]]


def fetch_klines_window(symbol: str, end_ms: int, limit: int) -> list[list]:
    """Fetch klines from Binance REST. Returns raw rows."""
    params = {
        "symbol": symbol,
        "interval": "1m",
        "limit": limit,
        "endTime": end_ms,
    }
    for attempt in range(3):
        try:
            resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
            if resp.status_code == 429:
                wait = 2 ** attempt
                log.warning("[%s] rate limited, waiting %ds", symbol, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == 2:
                raise
            log.warning("[%s] fetch retry %d: %s", symbol, attempt + 1, e)
            time.sleep(2 ** attempt)
    return []


def fetch_history(symbol: str, end_ms: int, days: int) -> list[list]:
    """Paginate backward from end_ms in 1000-candle windows covering `days`.

    Returns rows sorted ascending by open_time (oldest first).
    """
    target_ms = days * 24 * 3600 * 1000
    start_ms = end_ms - target_ms
    rows: list[list] = []
    cursor = end_ms
    page = 0
    while cursor > start_ms:
        page += 1
        batch = fetch_klines_window(symbol, cursor, BINANCE_KLINE_MAX)
        if not batch:
            log.warning("[%s] page %d: no candles returned, stopping", symbol, page)
            break
        rows = batch + rows  # prepend (older)
        # Binance returns rows ascending by open_time. The oldest row's open
        # time tells us how far back we got.
        oldest = int(batch[0][0])
        if oldest >= cursor:
            log.warning("[%s] page %d: no progress (oldest=%d >= cursor=%d)",
                        symbol, page, oldest, cursor)
            break
        cursor = oldest
        log.info("[%s] page %d: fetched %d candles, oldest=%d",
                 symbol, page, len(batch), oldest)
        # Soft rate limit.
        time.sleep(0.10)
    return rows


def write_klines_to_redis(
    r: redis.Redis,
    symbol: str,
    rows: Iterable[list],
    update_latest: bool,
) -> int:
    """Write kline rows to Redis in the canonical LMView shape.

    Each Binance row:
        [openTime, open, high, low, close, volume, closeTime,
         quoteAssetVolume, numberOfTrades, takerBuyBaseVol,
         takerBuyQuoteVol, ignore]

    Canonical candle JSON:
        {"t": openTime_ms, "o": float, "h": float, "l": float, "c": float,
         "v": float, "qv": float, "n": int, "x": bool}
    """
    history_key = f"candle:1m:{EXCHANGE}:{symbol}"
    ttl = TTL_1M_SEC

    pipe = r.pipeline()
    zadd_members: dict[str, float] = {}
    latest_payload: dict[str, str] | None = None
    latest_open_time: int | None = None

    for row in rows:
        open_time = int(row[0])
        # Historical rows from REST are all closed; mark x=True.
        # The most recent row from Binance may be the currently-forming
        # candle; mark it as not closed so the live writer can update it.
        close_time = int(row[6])
        is_closed = close_time <= int(time.time() * 1000)

        candle = {
            "t": open_time,
            "o": float(row[1]),
            "h": float(row[2]),
            "l": float(row[3]),
            "c": float(row[4]),
            "v": float(row[5]),
            "qv": float(row[7]),
            "n": int(row[8]),
            "x": is_closed,
        }
        zadd_members[json.dumps(candle, separators=(",", ":"))] = float(open_time)
        if latest_open_time is None or open_time > latest_open_time:
            latest_open_time = open_time
            latest_payload = {
                "open":         str(candle["o"]),
                "high":         str(candle["h"]),
                "low":          str(candle["l"]),
                "close":        str(candle["c"]),
                "volume":       str(candle["v"]),
                "quote_volume": str(candle["qv"]),
                "trade_count":  str(candle["n"]),
                "is_closed":    "1" if is_closed else "0",
                "kline_start":  str(open_time),
                "interval":     "1m",
                "exchange":     EXCHANGE,
            }

    if not zadd_members:
        return 0

    pipe.zadd(history_key, zadd_members)
    pipe.expire(history_key, ttl)

    if update_latest and latest_payload is not None:
        latest_key = f"candle:latest:{EXCHANGE}:{symbol}"
        pipe.hset(latest_key, mapping=latest_payload)
        pipe.expire(latest_key, ttl)

    pipe.execute()
    return len(zadd_members)


def symbol_has_redis_data(r: redis.Redis, symbol: str) -> bool:
    """Return True if symbol already has any 1m candles in Redis."""
    return bool(r.zcard(f"candle:1m:{EXCHANGE}:{symbol}"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbols", default="",
        help="Comma-separated symbols. Default: top-N by 24h quote volume.",
    )
    parser.add_argument("--top", type=int, default=100,
                        help="Top-N symbols when --symbols is empty (default 100)")
    parser.add_argument("--days", type=int, default=7,
                        help="Days of history to backfill (default 7)")
    parser.add_argument("--only-with-data", action="store_true",
                        help="Skip symbols with zero existing Redis data")
    parser.add_argument("--update-latest", action="store_true",
                        help="Overwrite candle:latest:* with backfilled latest")
    parser.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO"))
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.symbols.strip():
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        log.info("Fetching top-%d USDT symbols by 24h quote volume...", args.top)
        symbols = fetch_top_symbols(args.top)

    log.info("Backfilling %d symbols × %d days of 1m candles", len(symbols), args.days)

    r = get_redis_client()
    try:
        r.ping()
    except Exception as e:
        log.error("Redis ping failed: %s", e)
        return 2

    end_ms = int(time.time() * 1000)
    ok = 0
    failed: list[str] = []
    skipped: list[str] = []
    total_candles = 0

    for i, sym in enumerate(symbols, 1):
        try:
            if args.only_with_data and not symbol_has_redis_data(r, sym):
                skipped.append(sym)
                continue

            rows = fetch_history(sym, end_ms, args.days)
            if not rows:
                log.warning("[%d/%d] %s: no history returned", i, len(symbols), sym)
                failed.append(sym)
                continue

            written = write_klines_to_redis(
                r, sym, rows, update_latest=args.update_latest,
            )
            total_candles += written
            ok += 1
            oldest = int(rows[0][0])
            newest = int(rows[-1][0])
            log.info(
                "[%d/%d] %s OK: %d candles (oldest=%d, newest=%d, %.1f days span)",
                i, len(symbols), sym, written,
                oldest, newest, (newest - oldest) / 86_400_000,
            )
        except Exception as e:
            log.error("[%d/%d] %s FAILED: %s", i, len(symbols), sym, e)
            failed.append(sym)

    log.info(
        "Done: %d/%d symbols OK, %d failed, %d skipped. Total candles written: %d.",
        ok, len(symbols), len(failed), len(skipped), total_candles,
    )
    if failed:
        log.warning("Failed symbols: %s", ", ".join(failed[:20]))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
