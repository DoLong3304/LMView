#!/usr/bin/env python3
"""
Refresh Redis candle cache from Binance REST API.

The producer's WebSocket path is permanently 403'd from this AWS region
(Binance ELB geofencing). When the producer dies, the Redis caches
``candle:1m:*`` and ``candle:1s:*`` go stale and the frontend chart
"snaps" because it bridges an 11h gap between the last historical candle
and the live ticker.

This script is a one-shot / scheduled REST fallback that pulls recent
klines from ``api.binance.com`` (REST is NOT geofenced, only WS is) and
writes them to Redis in the exact shape produced by ``keydb_kline.py`` /
``DirectRedisWriter`` so the existing backend reads are transparent.

Redis key shapes written:
    candle:1m:{exchange}:{symbol}     ZADD sorted set, score = open_time_ms
    candle:latest:{exchange}:{symbol} HSET latest candle (1m only)
    candle:1s:{exchange}:{symbol}     ZADD sorted set (optional, --with-1s)

Usage:
    # Refresh top-25 USDT symbols by 24h quote volume, 500 1m candles each
    python scripts/refresh_redis_klines.py

    # Specific symbols
    python scripts/refresh_redis_klines.py --symbols BTCUSDT,ETHUSDT

    # Also backfill 1s candles (last 60)
    python scripts/refresh_redis_klines.py --with-1s --limit-1s 60

Env (read from container / host):
    REDIS_SENTINELS      comma-separated host:port list (preferred)
    REDIS_HOST           fallback single Redis host
    REDIS_PORT           fallback Redis port (default 6379)
    REDIS_MASTER_NAME    Sentinel master name (default mymaster)
    REDIS_PASSWORD       optional password

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

log = logging.getLogger("refresh_redis_klines")

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"
EXCHANGE = "binance"

# Match keydb_kline.py retention defaults so we don't shorten existing TTLs.
TTL_1M_SEC = max(int(os.environ.get("KEYDB_1M_RETENTION_DAYS", "7")), 1) * 86_400
TTL_1S_SEC = max(int(os.environ.get("KEYDB_1S_RETENTION_DAYS", "1")), 1) * 86_400

# Stablecoin / fiat pairs that are not crypto-to-crypto trades we want on the
# heatmap. Mirrors typical symbol filtering in src/exchanges/binance/client.py.
SYMBOL_BLACKLIST_PREFIXES = (
    "USDC", "FDUSD", "TUSDC", "USDP", "USD1", "EUR", "GBP", "TRY",
    "AEUR", "EURI", "USDS",
)


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


def fetch_klines(symbol: str, interval: str, limit: int) -> list[list]:
    """Fetch klines from Binance REST. Returns raw rows."""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    for attempt in range(3):
        try:
            resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
            if resp.status_code == 429:
                # rate limited — back off and retry
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


def write_klines_to_redis(
    r: redis.Redis,
    symbol: str,
    interval: str,
    rows: Iterable[list],
    update_latest: bool,
) -> int:
    """Write kline rows to Redis in the canonical LMView shape.

    Each Binance row:
        [openTime, open, high, low, close, volume, closeTime,
         quoteAssetVolume, numberOfTrades, takerBuyBaseVol,
         takerBuyQuoteVol, ignore]

    Canonical candle JSON (must match keydb_kline.py / DirectRedisWriter):
        {"t": openTime_ms, "o": float, "h": float, "l": float, "c": float,
         "v": float, "qv": float, "n": int, "x": bool}
    """
    history_key = f"candle:{interval}:{EXCHANGE}:{symbol}"
    ttl = TTL_1M_SEC if interval != "1s" else TTL_1S_SEC

    pipe = r.pipeline()
    zadd_members: dict[str, float] = {}
    latest_payload: dict[str, str] | None = None
    latest_open_time: int | None = None

    for row in rows:
        open_time = int(row[0])
        candle = {
            "t": open_time,
            "o": float(row[1]),
            "h": float(row[2]),
            "l": float(row[3]),
            "c": float(row[4]),
            "v": float(row[5]),
            "qv": float(row[7]),
            "n": int(row[8]),
            "x": True,  # REST only returns closed candles for historical, last one may be forming
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
                "is_closed":    "1",
                "kline_start":  str(open_time),
                "interval":     interval,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbols", default="",
        help="Comma-separated symbols. Default: top-N by 24h quote volume.",
    )
    parser.add_argument("--top", type=int, default=25, help="Top-N symbols (default 25)")
    parser.add_argument("--limit", type=int, default=500, help="1m candles per symbol (default 500)")
    parser.add_argument("--with-1s", action="store_true", help="Also refresh 1s candles")
    parser.add_argument("--limit-1s", type=int, default=60, help="1s candles per symbol (default 60)")
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

    log.info("Refreshing %d symbols: %s", len(symbols), ", ".join(symbols))

    r = get_redis_client()
    try:
        r.ping()
    except Exception as e:
        log.error("Redis ping failed: %s", e)
        return 2

    ok = 0
    failed: list[str] = []
    total_1m = 0
    total_1s = 0

    for i, sym in enumerate(symbols, 1):
        try:
            rows_1m = fetch_klines(sym, "1m", args.limit)
            if not rows_1m:
                log.warning("[%d/%d] %s: no 1m klines returned", i, len(symbols), sym)
                failed.append(sym)
                continue
            written_1m = write_klines_to_redis(r, sym, "1m", rows_1m, update_latest=True)
            total_1m += written_1m

            written_1s = 0
            if args.with_1s:
                rows_1s = fetch_klines(sym, "1s", args.limit_1s)
                if rows_1s:
                    written_1s = write_klines_to_redis(r, sym, "1s", rows_1s, update_latest=False)
                    total_1s += written_1s

            ok += 1
            last_close = float(rows_1m[-1][4])
            log.info(
                "[%d/%d] %s OK: %d 1m%s candles, last close %.4f",
                i, len(symbols), sym, written_1m,
                f" + {written_1s} 1s" if args.with_1s else "",
                last_close,
            )
            # Soft rate limit — Binance allows 1200 req/min but be safe.
            time.sleep(0.15)
        except Exception as e:
            log.error("[%d/%d] %s FAILED: %s", i, len(symbols), sym, e)
            failed.append(sym)

    log.info(
        "Done: %d/%d symbols OK, %d failed. Total 1m=%d, 1s=%d.",
        ok, len(symbols), len(failed), total_1m, total_1s,
    )
    if failed:
        log.warning("Failed symbols: %s", ", ".join(failed))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
