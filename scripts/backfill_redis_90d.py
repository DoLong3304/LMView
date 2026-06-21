#!/usr/bin/env python3
"""
90-day historical Redis candle backfill via Binance REST API.

Fetches up to 90 days of 1m candles for ALL Binance USDT trading symbols
(excluding stablecoins and fiat pairs) and writes them into Redis using a
separate 90-day retention bucket that does NOT interfere with the live
7-day retention writer.

Redis key shapes written (separate namespace from live writer):
    History (sorted set, 95d TTL):
        ZADD candle:1m:90d:binance:{symbol} {open_time_ms} '{json}'
        EXPIRE candle:1m:90d:binance:{symbol} 95*86400
    Latest (hash, 95d TTL):
        HSET candle:latest:90d:binance:{symbol} {open,high,...,interval,exchange}
        EXPIRE candle:latest:90d:binance:{symbol} 95*86400

ZADD with the same member+score is idempotent, so re-running this script is
safe — it fills gaps without overwriting newer candles.

Usage:
    # Backfill 90 days of 1m candles for all USDT symbols (no blacklist of stablecoins only)
    python scripts/backfill_redis_90d.py

    # Smaller symbol set for testing
    python scripts/backfill_redis_90d.py --symbols BTCUSDT,ETHUSDT,SOLUSDT

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
import urllib.request
import urllib.parse
from typing import Iterable

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write("redis package not installed. pip install redis\n")
    raise

import urllib.error

log = logging.getLogger("backfill_redis_90d")

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"
EXCHANGE = "binance"

# Match the 90-day backfill bucket.
TTL_95D_SEC = 95 * 86_400

# Stablecoin / fiat prefixes to skip.
# Excludes both stablecoins (pegged to USD) and fiat-quoted pairs (no crypto exposure).
SYMBOL_BLACKLIST_PREFIXES = (
    "USDC", "FDUSD", "TUSDC", "USDP", "USD1", "EUR", "GBP", "TRY",
    "AEUR", "EURI", "USDS", "BUSD", "TUSD", "DAI", "PAX", "SUSD",
)

# Binance REST kline API max per-request limit.
BINANCE_KLINE_MAX = 1000

# Be polite: Binance public REST allows ~1200 req/min from a single IP.
INTER_REQUEST_SLEEP_SEC = 0.15
INTER_PAGE_SLEEP_SEC = 0.10


def _http_get_json(url: str, params: dict | None = None, timeout: int = 15) -> object:
    """GET helper using stdlib only (no requests package required)."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "lmview-backfill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


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
        return sentinel.master_for(master_name, socket_timeout=10)

    host = os.environ.get("REDIS_HOST", "redis-master")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, socket_timeout=10, password=password)


def fetch_all_usdt_symbols() -> list[str]:
    """Return ALL Binance USDT trading symbols, filtering stablecoins.

    Unlike the 7-day writer, this returns every symbol that ends in USDT
    and is not a stablecoin/fiat pair.
    """
    rows = _http_get_json(BINANCE_24HR_URL, timeout=20)
    symbols = sorted({
        r["symbol"] for r in rows
        if r["symbol"].endswith("USDT")
        and not r["symbol"].startswith(SYMBOL_BLACKLIST_PREFIXES)
    })
    return symbols


def fetch_klines_window(symbol: str, end_ms: int, limit: int) -> list[list]:
    """Fetch one window of klines from Binance REST ending at end_ms (exclusive)."""
    params = {
        "symbol": symbol,
        "interval": "1m",
        "limit": limit,
        "endTime": end_ms,
    }
    for attempt in range(3):
        try:
            rows = _http_get_json(BINANCE_KLINES_URL, params=params, timeout=20)
            return rows
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt * 5
                log.warning("[%s] rate limited, waiting %ds", symbol, wait)
                time.sleep(wait)
                continue
            if attempt == 2:
                raise
            log.warning("[%s] fetch retry %d: HTTP %s", symbol, attempt + 1, e.code)
            time.sleep(2 ** attempt)
        except Exception as e:
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
        oldest = int(batch[0][0])
        if oldest >= cursor:
            log.warning("[%s] page %d: no progress (oldest=%d >= cursor=%d)",
                        symbol, page, oldest, cursor)
            break
        cursor = oldest
        if page % 10 == 0:
            log.info("[%s] page %d: %d candles so far, oldest=%s",
                     symbol, page, len(rows),
                     time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(oldest / 1000)))
        time.sleep(INTER_PAGE_SLEEP_SEC)
    return rows


def write_klines_to_redis(
    r: redis.Redis,
    symbol: str,
    rows: Iterable[list],
    update_latest: bool,
) -> int:
    """Write kline rows to Redis under the 90-day namespace.

    Each Binance row:
        [openTime, open, high, low, close, volume, closeTime,
         quoteAssetVolume, numberOfTrades, takerBuyBaseVol,
         takerBuyQuoteVol, ignore]

    Canonical candle JSON (matches live writer shape):
        {"t": openTime_ms, "o": float, "h": float, "l": float, "c": float,
         "v": float, "qv": float, "n": int, "x": bool}
    """
    history_key = f"candle:1m:90d:{EXCHANGE}:{symbol}"
    ttl = TTL_95D_SEC

    pipe = r.pipeline()
    zadd_members: dict[str, float] = {}
    latest_payload: dict[str, str] | None = None
    latest_open_time: int | None = None
    now_ms = int(time.time() * 1000)

    for row in rows:
        open_time = int(row[0])
        close_time = int(row[6])
        is_closed = close_time <= now_ms

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
        latest_key = f"candle:latest:90d:{EXCHANGE}:{symbol}"
        pipe.hset(latest_key, mapping=latest_payload)
        pipe.expire(latest_key, ttl)

    pipe.execute()
    return len(zadd_members)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbols", default="",
        help="Comma-separated symbols. Default: all USDT symbols from Binance.",
    )
    parser.add_argument("--days", type=int, default=90,
                        help="Days of history to backfill (default 90)")
    parser.add_argument("--update-latest", action="store_true",
                        help="Overwrite candle:latest:90d:* with backfilled latest")
    parser.add_argument("--dry-run", action="store_true",
                        help="List symbols that would be backfilled and exit")
    parser.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO"))
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Log progress every N symbols (default 50)")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.symbols.strip():
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        log.info("Fetching all Binance USDT symbols (excluding stablecoins)...")
        symbols = fetch_all_usdt_symbols()

    log.info("Will backfill %d symbols × %d days of 1m candles", len(symbols), args.days)

    if args.dry_run:
        log.info("Dry run - symbols that would be processed:")
        for i, s in enumerate(symbols, 1):
            print(f"  {i:4d}. {s}")
        return 0

    r = get_redis_client()
    try:
        r.ping()
    except Exception as e:
        log.error("Redis ping failed: %s", e)
        return 2

    end_ms = int(time.time() * 1000)
    ok = 0
    failed: list[tuple[str, str]] = []
    total_candles = 0
    started_at = time.time()

    for i, sym in enumerate(symbols, 1):
        try:
            rows = fetch_history(sym, end_ms, args.days)
            if not rows:
                log.warning("[%d/%d] %s: no history returned", i, len(symbols), sym)
                failed.append((sym, "no_history"))
                continue

            written = write_klines_to_redis(
                r, sym, rows, update_latest=args.update_latest,
            )
            total_candles += written
            ok += 1
            oldest = int(rows[0][0])
            newest = int(rows[-1][0])
            span_days = (newest - oldest) / 86_400_000

            elapsed = time.time() - started_at
            avg = elapsed / i
            eta = avg * (len(symbols) - i)
            log.info(
                "[%d/%d] %s OK: %d candles, span=%.1fd, elapsed=%.0fs eta=%.0fs",
                i, len(symbols), sym, written, span_days, elapsed, eta,
            )

            time.sleep(INTER_REQUEST_SLEEP_SEC)

        except Exception as e:
            log.error("[%d/%d] %s FAILED: %s", i, len(symbols), sym, e)
            failed.append((sym, str(e)))
            # Continue with next symbol on failure.

    log.info(
        "DONE: %d/%d symbols OK, %d failed. Total candles: %d. Elapsed: %.0fs.",
        ok, len(symbols), len(failed), total_candles, time.time() - started_at,
    )
    if failed:
        log.warning("Failed symbols (first 20): %s",
                    ", ".join(f"{s}({err})" for s, err in failed[:20]))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
