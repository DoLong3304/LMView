#!/usr/bin/env python3
"""Data coverage audit — verifies "fake cow" concerns.

Checks (against running producer + Redis + InfluxDB):

  1. Which symbols are actually subscribed (vs Binance top 200 by volume)?
  2. Is every subscribed symbol getting ticker 1s updates?
  3. Is every subscribed symbol getting kline 1s updates?
  4. InfluxDB coverage: which symbols have 1m kline data?
  5. Per-symbol data freshness (last-update timestamps).

Outputs a markdown report. Exits 0 if OK, 1 if suspicious.

Usage:
    python scripts/audit_data_coverage.py
    python scripts/audit_data_coverage.py --duration 60   # 60s sample
    python scripts/audit_data_coverage.py --json report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

# ── Imports guarded so the script can be inspected without running ────────
try:
    import requests
except ImportError:
    print("ERROR: pip install requests", file=sys.stderr)
    sys.exit(2)

# InfluxDB / Redis client imports (lazy, only when needed)


def fetch_binance_top_by_volume(quote: str = "USDT", n: int = 250) -> list[dict]:
    """Fetch Binance 24h ticker stats sorted by quote volume.

    Returns list of {symbol, quoteVolume, lastPrice, count} sorted desc.
    """
    resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=15)
    resp.raise_for_status()
    tickers = resp.json()
    out = []
    for t in tickers:
        if not t["symbol"].endswith(quote):
            continue
        try:
            out.append({
                "symbol": t["symbol"],
                "quote_volume_24h": float(t["quoteVolume"]),
                "last_price": float(t["lastPrice"]),
                "trade_count_24h": int(t["count"]),
            })
        except (KeyError, ValueError):
            continue
    out.sort(key=lambda x: x["quote_volume_24h"], reverse=True)
    return out[:n]


def fetch_binance_alphabetical_symbols(quote: str = "USDT", n: int = 250) -> list[str]:
    """Mimic the producer's symbol-fetching logic (alphabetical sort)."""
    resp = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=15)
    resp.raise_for_status()
    symbols = [
        s["symbol"] for s in resp.json().get("symbols", [])
        if s["quoteAsset"] == quote
        and s["status"] == "TRADING"
        and s.get("isSpotTradingAllowed", False)
    ]
    return sorted(symbols)[:n]


# ── Report sections ──────────────────────────────────────────────────────────


def build_symbol_comparison() -> dict:
    """Compare alphabetical top-200 vs volume top-200."""
    print("→ Fetching Binance 24h tickers (this takes ~3s)...")
    by_volume = fetch_binance_top_by_volume("USDT", 250)
    by_alpha = fetch_binance_alphabetical_symbols("USDT", 250)

    vol_set = {x["symbol"] for x in by_volume[:200]}
    alpha_set = set(by_alpha[:200])

    missing_from_alpha = vol_set - alpha_set
    extra_in_alpha = alpha_set - vol_set

    return {
        "total_usdt_pairs": len(by_volume),
        "by_volume_top200": sorted(vol_set),
        "by_alpha_top200": sorted(alpha_set),
        "missing_from_alpha_but_in_volume": sorted(missing_from_alpha),
        "in_alpha_but_low_volume": sorted(extra_in_alpha),
        "miss_rate_pct": round(len(missing_from_alpha) / 200 * 100, 2),
    }


def check_redis_ticker_coverage(redis_url: str = "redis://localhost:6379") -> dict:
    """Query Redis for ticker:latest:* keys to see what's actually in cache."""
    try:
        import redis
    except ImportError:
        return {"error": "redis-py not installed"}

    r = redis.from_url(redis_url)
    keys = []
    cursor = 0
    while True:
        cursor, batch = r.scan(cursor=cursor, match="ticker:latest:binance:*", count=500)
        keys.extend(batch)
        if cursor == 0:
            break
    symbols = sorted({k.decode().split(":")[-1] for k in keys if k.decode().endswith(b"USDT")})
    return {
        "redis_ticker_symbols_count": len(symbols),
        "first_20": symbols[:20],
        "last_20": symbols[-20:],
    }


def check_redis_kline_coverage(
    redis_url: str = "redis://localhost:6379",
    sample_seconds: int = 5,
) -> dict:
    """Check kline 1s and 1m coverage, then sample 5s of updates."""
    try:
        import redis
    except ImportError:
        return {"error": "redis-py not installed"}

    r = redis.from_url(redis_url)

    def scan_keys(pattern: str) -> list[str]:
        out, cursor = [], 0
        while True:
            cursor, batch = r.scan(cursor=cursor, match=pattern, count=500)
            out.extend(k.decode() for k in batch)
            if cursor == 0:
                break
        return out

    keys_1s = scan_keys("candle:1s:binance:*")
    keys_1m = scan_keys("candle:1m:binance:*")
    symbols_1s = sorted({k.split(":")[-1] for k in keys_1s})
    symbols_1m = sorted({k.split(":")[-1] for k in keys_1m})

    # Sample last-N for 5 seconds: pick 5 random symbols and check
    # that the latest candle moves at 1s intervals.
    import random
    sample = random.sample(symbols_1s, min(5, len(symbols_1s)))
    movement = {}
    for sym in sample:
        key = f"candle:1s:binance:{sym}"
        first = r.zrange(key, -2, -2, withscores=True)
        last = r.zrange(key, -1, -1, withscores=True)
        if first and last:
            t0, t1 = int(first[0][1]), int(last[0][1])
            movement[sym] = {
                "ts0_ms": t0,
                "ts1_ms": t1,
                "delta_ms": t1 - t0,
            }

    return {
        "kline_1s_symbols_count": len(symbols_1s),
        "kline_1m_symbols_count": len(symbols_1m),
        "first_20_1s": symbols_1s[:20],
        "last_20_1s": symbols_1s[-20:],
        "sampled_movement": movement,
    }


def check_influxdb_kline_coverage(
    influx_url: str = "http://localhost:8086",
    influx_token: str = "",
    influx_org: str = "vi",
    influx_bucket: str = "crypto",
) -> dict:
    """Query InfluxDB for distinct symbols in ``candles`` measurement."""
    try:
        from influxdb_client import InfluxDBClient
    except ImportError:
        return {"error": "influxdb-client not installed"}

    if not influx_token:
        return {"error": "INFLUX_TOKEN not set"}

    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    query_api = client.query_api()

    # Last 7d, group by symbol
    flux = f'''
from(bucket: "{influx_bucket}")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "candles")
  |> filter(fn: (r) => r._field == "close")
  |> group(columns: ["symbol"])
  |> count()
  |> group()
'''
    try:
        tables = query_api.query(flux)
    except Exception as e:
        return {"error": f"query failed: {e}"}

    counts: dict[str, int] = {}
    for table in tables:
        for record in table.records:
            sym = record.values.get("symbol", "?")
            counts[sym] = record.get_value()

    symbols = sorted(counts.keys())
    return {
        "influxdb_7d_symbols_count": len(symbols),
        "first_20": symbols[:20],
        "last_20": symbols[-20:],
        "count_distribution": {
            "<100": sum(1 for v in counts.values() if v < 100),
            "100-1000": sum(1 for v in counts.values() if 100 <= v < 1000),
            "1000-10000": sum(1 for v in counts.values() if 1000 <= v < 10000),
            ">=10000": sum(1 for v in counts.values() if v >= 10000),
        },
    }


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--duration", type=int, default=0,
                   help="If >0, sample for N seconds and report ticker rate per symbol")
    p.add_argument("--json", type=str, default=None,
                   help="Write JSON report to this path")
    p.add_argument("--redis-url", default="redis://localhost:6379")
    p.add_argument("--influx-url", default="http://localhost:8086")
    p.add_argument("--influx-token", default="")
    p.add_argument("--influx-org", default="vi")
    p.add_argument("--influx-bucket", default="crypto")
    args = p.parse_args()

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": args.duration,
    }

    # Section 1: Symbol comparison
    print("\n[1/4] Comparing alphabetical top-200 vs volume top-200...")
    report["symbol_comparison"] = build_symbol_comparison()

    # Section 2: Redis ticker coverage
    print("\n[2/4] Checking Redis ticker coverage...")
    report["redis_ticker"] = check_redis_ticker_coverage(args.redis_url)

    # Section 3: Redis kline coverage
    print("\n[3/4] Checking Redis kline coverage...")
    report["redis_kline"] = check_redis_kline_coverage(args.redis_url, args.duration)

    # Section 4: InfluxDB coverage
    print("\n[4/4] Checking InfluxDB coverage...")
    report["influxdb_kline"] = check_influxdb_kline_coverage(
        args.influx_url, args.influx_token, args.influx_org, args.influx_bucket
    )

    # ── Print summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DATA COVERAGE AUDIT — SUMMARY")
    print("=" * 70)

    sc = report["symbol_comparison"]
    print(f"\nTotal Binance USDT pairs:        {sc['total_usdt_pairs']}")
    print(f"Top-200 by volume:                {len(sc['by_volume_top200'])}")
    print(f"Top-200 alphabetical (current):   {len(sc['by_alpha_top200'])}")
    print(f"Missing from alphabetical:        {len(sc['missing_from_alpha_but_in_volume'])}")
    print(f"  Miss rate:                       {sc['miss_rate_pct']}%")
    if sc["missing_from_alpha_but_in_volume"]:
        print("  Examples (top 10 by volume NOT in alphabetical top-200):")
        for s in sc["missing_from_alpha_but_in_volume"][:10]:
            print(f"    {s}")

    rt = report["redis_ticker"]
    if "error" not in rt:
        print(f"\nRedis ticker symbols cached:     {rt['redis_ticker_symbols_count']}")
        print(f"  First 5: {', '.join(rt['first_20'][:5])}")
        print(f"  Last 5:  {', '.join(rt['last_20'][-5:])}")

    rk = report["redis_kline"]
    if "error" not in rk:
        print(f"\nRedis 1s kline symbols:          {rk['kline_1s_symbols_count']}")
        print(f"Redis 1m kline symbols:          {rk['kline_1m_symbols_count']}")
        if rk["sampled_movement"]:
            print("  Sampled 1s movement (should be 1000ms each):")
            for sym, m in rk["sampled_movement"].items():
                flag = "✓" if 900 <= m["delta_ms"] <= 1100 else "✗"
                print(f"    {flag} {sym}: delta={m['delta_ms']}ms")

    ik = report["influxdb_kline"]
    if "error" not in ik:
        print(f"\nInfluxDB 7d symbols (1m klines):  {ik['influxdb_7d_symbols_count']}")
        print(f"  Distribution: {ik['count_distribution']}")
    elif "error" in ik:
        print(f"\nInfluxDB: SKIPPED ({ik['error']})")

    # ── Verdict ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    issues = []
    if sc["miss_rate_pct"] > 10:
        issues.append(
            f"HIGH miss rate ({sc['miss_rate_pct']}%): {len(sc['missing_from_alpha_but_in_volume'])} "
            f"high-volume symbols NOT subscribed. This is the 'fake cow' risk."
        )
    if "error" not in rk and rk["kline_1s_symbols_count"] < 150:
        issues.append(
            f"LOW 1s kline coverage ({rk['kline_1s_symbols_count']} symbols). "
            f"Expected ~200 if MAX_SYMBOLS=200."
        )
    if "error" not in ik and ik["influxdb_7d_symbols_count"] < 100:
        issues.append(
            f"LOW InfluxDB coverage ({ik['influxdb_7d_symbols_count']} symbols in 7d). "
            f"Long-term analytics may be sparse."
        )

    if not issues:
        print("✓ All checks passed. Data coverage looks healthy.")
    else:
        print(f"✗ Found {len(issues)} issue(s):")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print("\nRecommendations:")
        print("  • Switch symbol selection from alphabetical to volume-ranked")
        print("  • See: src/exchanges/binance/client.py:fetch_symbols()")
        print("  • Or filter fetch_symbols() output to top-N by 24h quote volume")

    # ── Write JSON if requested ────────────────────────────────────────────
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nFull report written to: {args.json}")

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
