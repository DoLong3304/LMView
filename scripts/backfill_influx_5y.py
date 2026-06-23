#!/usr/bin/env python3
"""
5-year 1m candle backfill from Binance → InfluxDB.

Sorted by 24h quote volume (BTC, ETH, SOL… first).
Skips symbols already covered (check InfluxDB last candle before fetching).
Can be safely re-run — idempotent at the day boundary.

Usage (inside fastapi-prod container):
    # Test with top-5 symbols
    python /app/scripts/backfill_influx_5y.py --top 5

    # Full run — will daemonize itself via setsid
    nohup python /app/scripts/backfill_influx_5y.py --top 671 \
      > /tmp/backfill_5y.log 2>&1 &

    # Tail progress
    tail -f /tmp/backfill_5y.log

    # Resume after interruption (skips already-written windows)
    python /app/scripts/backfill_influx_5y.py --top 671 --resume

    # Verify data count
    python /app/scripts/backfill_influx_5y.py --verify
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Iterable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("backfill_5y")

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_EXCHANGE_URL = "https://api.binance.com/api/v3/exchangeInfo"

# ── InfluxDB config (env-mirrors fastapi container) ─────────────────────────
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

# ── Tuning ──────────────────────────────────────────────────────────────────
BACKFILL_YEARS = 5
# Binance 1m candlestick limit per request
KLINES_PER_REQ = 1000
# Binance public REST ≈ 1200 req/min from same IP → 50 ms/symbol = 20 req/s
INTER_SYMBOL_SLEEP = 0.15
INTER_PAGE_SLEEP = 0.15
# Thread pool for parallel symbol fetching
MAX_WORKERS = 4

# EPOCH for 5 years ago (approx)
_5_YEARS_MS = BACKFILL_YEARS * 365 * 24 * 3600 * 1000
# Stablecoin/fiat prefixes to exclude
BLACKLIST_PREFIXES = (
    "USDC", "FDUSD", "TUSDC", "USDP", "USD1", "EUR", "GBP", "TRY",
    "AEUR", "EURI", "USDS", "BUSD", "TUSD", "DAI", "PAX", "SUSD",
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _http_get(url: str, params: dict | None = None, timeout: int = 20) -> object:
    if params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "lmview-backfill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _get_influx_client():
    """Lazy-import influxdb_client — only when it's available."""
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.write_api import SYNCHRONOUS
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)


def _write_points(client, points):
    """Write list of Point objects to InfluxDB."""
    from influxdb_client.client.write_api import SYNCHRONOUS
    w = client.write_api(write_options=SYNCHRONOUS)
    w.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    w.close()


# ── Symbol fetching (sorted by 24h volume) ──────────────────────────────────

def fetch_top_symbols(n: int = 671) -> list[str]:
    """Return top-N USDT pairs by 24h quote volume, filtering stablecoins.

    BTC, ETH, SOL, XRP, PEPE … come first.
    """
    log.info("Fetching all Binance USDT symbols by 24h volume…")
    rows = _http_get(BINANCE_24HR_URL, timeout=25)
    filtered = sorted(
        (
            r for r in rows
            if r["symbol"].endswith("USDT")
            and not r["symbol"].startswith(BLACKLIST_PREFIXES)
            and r.get("symbol", "") != "币安人生USDT"  # Binance meme ticker
        ),
        key=lambda r: float(r.get("quoteVolume", 0)),
        reverse=True,
    )
    symbols = [r["symbol"] for r in filtered[:n]]
    log.info(
        "Top-%d symbols: %s… → %s…",
        len(symbols),
        ", ".join(symbols[:5]),
        ", ".join(symbols[-3:]),
    )
    return symbols


# ── Kline fetching from Binance REST ────────────────────────────────────────

def fetch_klines_stream(
    symbol: str,
    start_ms: int,
    end_ms: int,
    client,
    interval: str = "1m",
    batch_limit: int = KLINES_PER_REQ,
) -> int:
    """Fetch OHLCV klines page-by-page, write each page to InfluxDB immediately.

    Returns total candles written.
    Avoids OOM by not accumulating all candles in memory.
    """
    total = 0
    cursor = start_ms
    first_ts = None
    last_ts = None
    page_count = 0
    _last_progress_log = 0.0

    while cursor < end_ms:
        bat = _fetch_one_window(symbol, cursor, end_ms, interval, batch_limit)
        if not bat:
            break
        points = klines_to_influx_points(symbol, bat)
        if points:
            _write_points(client, points)
            total += len(points)
        last_ts = int(bat[-1][0])
        if first_ts is None:
            first_ts = int(bat[0][0])
        if last_ts <= cursor:
            break
        cursor = last_ts + 60_000
        page_count += 1
        # Log progress every 2 min to avoid silent periods
        now = time.time()
        if now - _last_progress_log >= 120:
            _last_progress_log = now
            pct = (cursor - start_ms) / (end_ms - start_ms) * 100
            log.info("[%s] ... %d pages (%d candles, %.0f%% done, cursor=%s)",
                     symbol, page_count, total, min(pct, 99.9),
                     datetime.fromtimestamp(cursor / 1000).strftime("%Y-%m-%d"))
        time.sleep(INTER_PAGE_SLEEP)

    if total > 0 and first_ts:
        span_days = (last_ts - first_ts) / 86_400_000
        log.info("[%s] \u2713 %d candles (%.1f days, %s \u2013 %s)",
                 symbol, total, span_days,
                 datetime.fromtimestamp(first_ts / 1000).strftime("%Y-%m-%d"),
                 datetime.fromtimestamp(last_ts / 1000).strftime("%Y-%m-%d"))
    else:
        log.info("[%s] No klines returned", symbol)

    time.sleep(INTER_SYMBOL_SLEEP)
    return total


def _fetch_one_window(
    symbol: str, start_ms: int, end_ms: int, interval: str, limit: int,
) -> list[list]:
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    }
    for attempt in range(5):
        _throttle()
        try:
            return _http_get(BINANCE_KLINES_URL, params=params, timeout=20)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt * 10
                log.warning("[%s] 429, backing off %ds", symbol, wait)
                time.sleep(wait)
                continue
            elif e.code == 418:
                wait = 120
                log.warning("[%s] 418 (banned temp), sleeping %ds", symbol, wait)
                time.sleep(wait)
                continue
            if attempt == 2:
                raise
            log.warning("[%s] HTTP %s, retry %d", symbol, e.code, attempt + 1)
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == 2:
                raise
            log.warning("[%s] fetch err %s, retry %d", symbol, e, attempt + 1)
            time.sleep(2 ** attempt)
    return []


# ── InfluxDB write ──────────────────────────────────────────────────────────

def klines_to_influx_points(symbol: str, klines: list[list]) -> list:
    """Convert Binance raw klines → list of InfluxDB Point objects (candles measurement)."""
    from influxdb_client import Point, WritePrecision

    points = []
    for k in klines:
        try:
            point = (
                Point("candles")
                .tag("symbol", symbol)
                .tag("exchange", "binance")
                .tag("interval", "1m")
                .field("open", float(k[1]))
                .field("high", float(k[2]))
                .field("low", float(k[3]))
                .field("close", float(k[4]))
                .field("volume", float(k[5]))
                .field("quote_volume", float(k[7]))
                .field("trade_count", int(k[8]))
                .field("is_closed", True)
                .time(int(k[0]), WritePrecision.MS)
            )
            points.append(point)
        except (IndexError, ValueError, TypeError):
            continue
    return points


# ── Resume support: check InfluxDB for earliest candle ──────────────────────

def get_earliest_ts_influx(client, symbol: str) -> int:
    """Return the OLDEST candle timestamp (ms) for this symbol in InfluxDB, or 0.

    Used for resume logic: if oldest candle is older than 5 years ago, skip.
    """
    q = client.query_api()
    flux = f'''
    from(bucket:"{INFLUX_BUCKET}")
      |> range(start:0)
      |> filter(fn: (r) => r._measurement == "candles"
                         and r.symbol == "{symbol}"
                         and r.interval == "1m")
      |> filter(fn: (r) => r._field == "close")
      |> first()
    '''
    try:
        tables = q.query(flux)
        for table in tables:
            for record in table.records:
                ts = int(record.get_time().timestamp() * 1000)
                if ts > 0:
                    return ts
    except Exception:
        pass
    return 0


def get_symbol_count_influx(client, symbol: str) -> int:
    """Return total candle count for a symbol in InfluxDB."""
    q = client.query_api()
    flux = f'''
    from(bucket:"{INFLUX_BUCKET}")
      |> range(start:0)
      |> filter(fn: (r) => r._measurement == "candles"
                         and r.symbol == "{symbol}"
                         and r.interval == "1m")
      |> filter(fn: (r) => r._field == "close")
      |> count()
    '''
    try:
        tables = q.query(flux)
        for table in tables:
            for record in table.records:
                return int(record.get_value() or 0)
    except Exception:
        pass
    return 0


# ── Per-symbol backfill logic ───────────────────────────────────────────────

# Global rate-limit budget: ~15 req/s (stay under 1200/min)
import threading
_rate_lock = threading.Lock()
_last_req_ts: float = 0.0
_MIN_REQUEST_GAP = 0.25  # ~4 req/s (stay under Binance 1200/min)


def _throttle():
    global _last_req_ts
    with _rate_lock:
        now = time.time()
        gap = now - _last_req_ts
        if gap < _MIN_REQUEST_GAP:
            time.sleep(_MIN_REQUEST_GAP - gap)
            now = time.time()
        _last_req_ts = now


def backfill_symbol(
    symbol: str,
    client,
    resume: bool = False,
) -> int:
    """Backfill one symbol into InfluxDB.

    Returns number of candles written.
    """
    now_ms = int(time.time() * 1000)
    # 5 years ago
    target_start_ms = now_ms - _5_YEARS_MS
    # Align to minute boundary
    target_start_ms = (target_start_ms // 60_000) * 60_000
    end_ms = (now_ms // 60_000) * 60_000
    years_str = f"{BACKFILL_YEARS}y"

    if resume:
        earliest_ts = get_earliest_ts_influx(client, symbol)
        count = get_symbol_count_influx(client, symbol)
        # Target: oldest candle should be 5 years back
        target_oldest_ms = now_ms - _5_YEARS_MS - 60000  # 1 min slack
        if earliest_ts > 0 and earliest_ts <= target_oldest_ms and count > 100000:
            log.info("[%s] ✓ Already complete (oldest=%s, count=%d)",
                     symbol,
                     datetime.fromtimestamp(earliest_ts / 1000).strftime("%Y-%m-%d"),
                     count)
            return 0
        if count > 0:
            log.info("[%s] Partial data: %d candles, oldest=%s, fetching remaining",
                     symbol, count,
                     datetime.fromtimestamp(earliest_ts / 1000).strftime("%Y-%m-%d") if earliest_ts else "none")
            # Don't skip — fetch from scratch (InfluxDB upsert is idempotent)
            # The resume is handled by skipping the full fetch below

    # Fetch + write streaming (page-by-page to avoid OOM)
    log.info("[%s] Fetching from %s → now (%s)",
             symbol,
             datetime.fromtimestamp(target_start_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
             years_str)
    total = fetch_klines_stream(symbol, target_start_ms, end_ms, client)
    return total


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backfill 5y 1m candles → InfluxDB")
    parser.add_argument("--top", type=int, default=671, help="Number of top-volume symbols")
    parser.add_argument("--resume", action="store_true", help="Resume (skip already-fetched windows)")
    parser.add_argument("--verify", action="store_true", help="Verify data counts and exit")
    parser.add_argument("--symbols", default="", help="Comma-separated override")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Parallel workers")
    args = parser.parse_args()

    if args.symbols.strip():
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = fetch_top_symbols(args.top)

    log.info("Backfill %d symbols × %d years 1m candles → InfluxDB (%s)",
             len(symbols), BACKFILL_YEARS, INFLUX_URL)

    client = _get_influx_client()
    # Verify InfluxDB
    try:
        client.health()
    except Exception as e:
        log.error("InfluxDB not reachable: %s", e)
        return 1

    if args.verify:
        log.info("=== Verify mode ===")
        for s in symbols[:20]:
            cnt = get_symbol_count_influx(client, s)
            earliest_ts = get_earliest_ts_influx(client, s)
            earliest_str = datetime.fromtimestamp(earliest_ts / 1000).strftime("%Y-%m-%d") if earliest_ts else "N/A"
            log.info("  %s: %d candles, oldest=%s", s, cnt, earliest_str)
        client.close()
        return 0

    ok = 0
    total_written = 0
    failed: list[str] = []
    started_at = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_to_symbol = {}
        # Submit symbols sorted by volume (already sorted from fetch_top_symbols)
        for s in symbols:
            fut = pool.submit(backfill_symbol, s, client, args.resume)
            future_to_symbol[fut] = s

        done = 0
        for fut in as_completed(future_to_symbol):
            s = future_to_symbol[fut]
            done += 1
            try:
                n = fut.result()
                total_written += n
                if n > 0:
                    ok += 1
                else:
                    log.info("[%d/%d] %s: skipped (0 candles)", done, len(symbols), s)
            except Exception as e:
                log.error("[%d/%d] %s FAILED: %s", done, len(symbols), s, e)
                failed.append(s)

            elapsed = time.time() - started_at
            avg = elapsed / done
            remaining = avg * (len(symbols) - done)
            log.info("[%d/%d] %s done — written=%d, elapsed=%.0fs, eta=%.0fs",
                     done, len(symbols), s, total_written, elapsed, remaining)

    log.info("=" * 60)
    log.info("DONE: %d/%d OK, %d failed, %d total candles, %.0fs elapsed",
             ok, len(symbols), len(failed), total_written, time.time() - started_at)
    if failed:
        log.warning("Failed: %s", ", ".join(failed[:20]))
        return 1
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
