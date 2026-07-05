#!/usr/bin/env python3
"""
5-year 1m candle backfill from Binance Data.vision (NO rate limits!).

Architecture:
- Each work item = one (symbol, month) or (symbol, day) ZIP to download
- 80+ concurrent HTTP workers download ZIPs from CloudFront (no rate limit)
- Each worker writes its own data directly to InfluxDB
- No shared state = no thread contention

Usage:
    # Test
    python /app/scripts/backfill_influx_vision.py --top 5

    # Full run (656 symbols)
    python /app/scripts/backfill_influx_vision.py --top 656
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("backfill_vision")

# ── Binance Data.vision ─────────────────────────────────────────────────────
VISION_BASE = "https://data.binance.vision/data/spot"
VISION_MONTHLY = f"{VISION_BASE}/monthly/klines"
VISION_DAILY = f"{VISION_BASE}/daily/klines"

# ── Binance REST (symbol list only) ─────────────────────────────────────────
BINANCE_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

# ── InfluxDB ────────────────────────────────────────────────────────────────
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

# ── Tuning ──────────────────────────────────────────────────────────────────
BACKFILL_YEARS = 5
DOWNLOAD_WORKERS = 80      # concurrent HTTP downloads


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "lmview-backfill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _get_influx_client():
    from influxdb_client import InfluxDBClient
    c = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        c.health()
    except Exception as e:
        log.error("InfluxDB unreachable: %s", e)
        raise
    return c


# ═══════════════════════════════════════════════════════════════════════════
#  SYMBOL LIST
# ═══════════════════════════════════════════════════════════════════════════

def fetch_top_symbols(n: int = 671) -> list[str]:
    log.info("Fetching top Binance USDT symbols…")
    rows = json.loads(_http_get(BINANCE_24HR_URL, timeout=25).decode())
    bl = ("USDC","FDUSD","TUSDC","USDP","USD1","EUR","GBP","TRY",
          "AEUR","EURI","USDS","BUSD","TUSD","DAI","PAX","SUSD")
    filtered = sorted(
        (r for r in rows if r["symbol"].endswith("USDT") and not r["symbol"].startswith(bl)),
        key=lambda r: float(r.get("quoteVolume", 0)), reverse=True,
    )
    symbols = [r["symbol"] for r in filtered[:n]]
    log.info("Top-%d: %s… → %s…", len(symbols), symbols[:3], symbols[-3:])
    return symbols


# ═══════════════════════════════════════════════════════════════════════════
#  BINANCE DATA.VISION DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════

def _month_url(sym: str, y: int, m: int) -> str:
    return f"{VISION_MONTHLY}/{sym}/1m/{sym}-1m-{y:04d}-{m:02d}.zip"

def _daily_url(sym: str, y: int, m: int, d: int) -> str:
    return f"{VISION_DAILY}/{sym}/1m/{sym}-1m-{y:04d}-{m:02d}-{d:02d}.zip"

def _months_range(sy: int, sm: int, ey: int, em: int):
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


def _parse_csv(raw: bytes) -> list[list]:
    """Parse ZIP → list of kline rows (12 fields each)."""
    rows = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            for line in z.read(name).decode("utf-8").strip().split("\n"):
                parts = line.strip().split(",")
                if len(parts) >= 12:
                    rows.append(parts[:12])
    return rows


def _rows_to_points(symbol: str, rows: list[list]) -> list:
    """Convert kline rows → InfluxDB Point objects."""
    from influxdb_client import Point, WritePrecision
    pts = []
    for k in rows:
        try:
            pts.append(
                Point("candles")
                .tag("symbol", symbol).tag("exchange", "binance").tag("interval", "1m")
                .field("open", float(k[1])).field("high", float(k[2]))
                .field("low", float(k[3])).field("close", float(k[4]))
                .field("volume", float(k[5])).field("quote_volume", float(k[7]))
                .field("trade_count", int(k[8])).field("is_closed", True)
                .time(int(k[0]) // 1000, WritePrecision.MS)
            )
        except (IndexError, ValueError, TypeError):
            continue
    return pts


def _write_points(client, symbol: str, points: list) -> int:
    """Write points to InfluxDB. Returns count written."""
    if not points:
        return 0
    from influxdb_client.client.write_api import SYNCHRONOUS
    w = client.write_api(write_options=SYNCHRONOUS)
    try:
        w.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
        return len(points)
    except Exception as e:
        log.error("[%s] InfluxDB write failed (%d pts): %s", symbol, len(points), e)
        return 0
    finally:
        try:
            w.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
#  PROCESS ONE WORK ITEM
# ═══════════════════════════════════════════════════════════════════════════

def _process_work(client, kind: str, symbol: str,
                  y: int, m: int, d: int | None,
                  start_ms: int, end_ms: int) -> tuple[str, int]:
    """Download → parse → write. Returns (symbol, candles_written)."""
    url = _daily_url(symbol, y, m, d) if kind == "daily" else _month_url(symbol, y, m)
    try:
        raw = _http_get(url, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return symbol, 0
        raise

    rows = _parse_csv(raw)
    # Filter by time range (Binance Vision timestamps are in μs, convert to ms)
    filtered = [r for r in rows if int(r[0]) // 1000 >= start_ms and int(r[0]) // 1000 < end_ms]
    if not filtered:
        return symbol, 0

    points = _rows_to_points(symbol, filtered)
    n = _write_points(client, symbol, points)
    return symbol, n


# ═══════════════════════════════════════════════════════════════════════════
#  BUILD WORK ITEMS
# ═══════════════════════════════════════════════════════════════════════════

def build_work(symbols: list[str]) -> list[tuple]:
    """Build list of work items (kind, sym, y, m, d, start_ms, end_ms)."""
    now = datetime.now(timezone.utc)
    end = now - timedelta(days=1)  # yesterday
    target_start = now - timedelta(days=BACKFILL_YEARS * 365)
    target_start_ms = int(target_start.timestamp() * 1000)
    target_end_ms = int(end.timestamp() * 1000)

    work = []
    for sym in symbols:
        start = target_start
        for y, m in _months_range(start.year, start.month, end.year, end.month):
            if y < end.year or (y == end.year and m < end.month):
                work.append(("monthly", sym, y, m, None, target_start_ms, target_end_ms))

        # Current month → daily files
        for d in range(1, end.day + 1):
            work.append(("daily", sym, end.year, end.month, d, target_start_ms, target_end_ms))

    return work


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--workers", type=int, default=DOWNLOAD_WORKERS)
    args = parser.parse_args()

    if args.symbols.strip():
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = fetch_top_symbols(args.top)

    log.info("Backfill %d symbols × %dy via Binance Data.vision → InfluxDB (%s)",
             len(symbols), BACKFILL_YEARS, INFLUX_URL)

    client = _get_influx_client()

    # Build ALL work items
    all_work = build_work(symbols)
    log.info("Total work items: %d (files to download)", len(all_work))

    if not all_work:
        log.info("Nothing to do!")
        client.close()
        return 0

    # Process in parallel
    done = 0
    failed = 0
    total_written = 0
    started_at = time.time()
    prev_log = 0.0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_process_work, client, *w) for w in all_work]

        for fut in as_completed(futures):
            done += 1
            try:
                sym, n = fut.result(timeout=120)
                total_written += n
            except Exception as e:
                failed += 1
                if failed <= 10:
                    log.error("Work item failed: %s", e)

            # Log progress every 5s
            t = time.time()
            if t - prev_log >= 5.0:
                prev_log = t
                elapsed = t - started_at
                rate = done / elapsed if elapsed > 0 else 0
                remaining = (len(all_work) - done) / rate if rate > 0 else 0
                if done % 50 == 0 or done == len(all_work):
                    log.info("[%d/%d] %.0f%% done, %d written, %d failed, %.0fs ETA",
                             done, len(all_work), done / len(all_work) * 100,
                             total_written, failed, remaining)

    elapsed = time.time() - started_at
    rate = total_written / elapsed if elapsed > 0 else 0
    log.info("=" * 55)
    log.info("DONE: %d files, %d/%d failed", done, failed, len(all_work))
    log.info("Candles written: %d in %.0fs (%.0f/s)", total_written, elapsed, rate)

    client.close()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
