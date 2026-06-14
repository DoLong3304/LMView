"""
Liquidity Heatmap aggregator (v0.24.5, Task 5).

Consumes partial order-book depth snapshots from the ``crypto_depth``
Kafka topic, buckets the resting order quantity by **distance from the
mid-price** (in basis-point increments) for both bid and ask sides,
and writes the bucketed quantities to InfluxDB as the
``liquidity_heatmap`` measurement.

## Why this exists

A line chart of order-book snapshots shows you the *current* book.
A heatmap shows you **where liquidity has been resting over time** —
which is what tells you "is this support level real or thin?".

The UI queries this measurement and renders a 2-D matrix
(time × price-bucket, color = quantity) per symbol. TradingView's
"Depth of Market" widget and Bookmap's footprint are the
industry references; this Gold table is the data substrate they
would consume.

## Bucketing strategy

For each depth snapshot:

1. Compute ``mid_price = (best_bid + best_ask) / 2``.
2. For each bid level at price ``p`` with quantity ``q``:
   - ``pct_distance = (mid_price - p) / mid_price * 100``   (>= 0)
   - ``bucket = floor(pct_distance / BUCKET_PCT)``          (>= 0)
   - Record ``quantity=q`` under tag ``side=bid``,
     ``price_bucket=<bucket>``.
3. Symmetric for asks (``pct_distance = (p - mid) / mid * 100``).

Default ``BUCKET_PCT = 0.1`` (10 basis points) and
``MAX_BUCKETS = 100`` — covers ±1% around the mid in 100 buckets
per side. Configurable via env vars ``HEATMAP_BUCKET_PCT`` and
``HEATMAP_MAX_BUCKETS``.

## Caveats

- **Exchange qualifier**: AGENTS.md flags that depth processing drops
  the ``exchange`` field downstream. We default to ``"binance"`` in
  v0.24.5; the writer accepts a real exchange in the input JSON and
  uses it if present, otherwise falls back to the constant. The
  manifest entry documents this.
- **Out-of-window levels**: any level further than
  ``BUCKET_PCT * MAX_BUCKETS`` from mid is silently dropped. A 10%
  move in BTC blows out ±1% liquidity visualisation; we accept that
  rather than ballooning the bucket space.

## Schema (see gold_schema_manifest.py for the canonical declaration)

    exchange        VARCHAR     (default 'binance')
    symbol          VARCHAR
    side            VARCHAR     ('bid' | 'ask')
    price_bucket    INTEGER     (0 = at mid, 1 = first level away, ...)
    quantity        DOUBLE      (sum of resting qty in this bucket + minute)
    order_count     BIGINT      (count of levels contributing)
    time_bucket     BIGINT      (minute epoch UTC; also the InfluxDB time)
    computed_at     BIGINT      (when the Flink task saw the snapshot)
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from typing import Iterable

# pyflink is only available in the Flink TaskManager image.
# We import FlatMapFunction for typing; the writer is also
# importable in tests where we stub pyflink (see test_liquidity_heatmap.py).
try:
    from pyflink.datastream.functions import FlatMapFunction
except ImportError:  # pragma: no cover - dev / CI path
    class FlatMapFunction:  # type: ignore[no-redef]
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Constants (env-overridable so ops can tune the bucket width)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_BUCKET_PCT = float(os.getenv("HEATMAP_BUCKET_PCT", "0.1"))
DEFAULT_MAX_BUCKETS = int(os.getenv("HEATMAP_MAX_BUCKETS", "100"))
DEFAULT_EXCHANGE = os.getenv("HEATMAP_DEFAULT_EXCHANGE", "binance")

# Per-writer metric labels
WRITER_NAME = "liquidity_heatmap"
SINK_NAME = "influxdb"
SOURCE_TOPIC = "crypto_depth"


# ─────────────────────────────────────────────────────────────────────────────
# Pure bucketing helpers (testable in isolation, no Flink / Influx)
# ─────────────────────────────────────────────────────────────────────────────


def compute_mid_price(best_bid, best_ask):
    """Return the mid-price from top-of-book, or None if either side empty.

    Accepts both numeric and string-typed prices (Binance wire format
    sends them as strings in some depth diff messages).
    """
    try:
        bid = float(best_bid)
        ask = float(best_ask)
    except (TypeError, ValueError):
        return None
    if bid <= 0 or ask <= 0:
        return None
    if ask < bid:
        # Inverted book; treat as None rather than crash the watermark.
        return None
    return (bid + ask) / 2.0


def price_to_bucket(price: float, mid_price: float,
                     bucket_pct: float = DEFAULT_BUCKET_PCT,
                     max_buckets: int = DEFAULT_MAX_BUCKETS) -> int | None:
    """Map an absolute price to a non-negative bucket index.

    Returns None for prices outside the configured range.

    ``bucket_pct`` is the width of one bucket in percent (e.g. 0.1 = 0.1%).
    ``max_buckets`` caps the return value; anything beyond is dropped.

    Implementation note: we use ``round()`` (not floor-division) because
    the input price may be a float with IEEE-754 representation error
    (e.g. 99.9 in JSON deserialises to 99.9 - ε).  ``distance // bucket_pct``
    can underflow to 0 for a price that's *just* inside a bucket boundary.
    """
    try:
        price_f = float(price)
        mid_f = float(mid_price)
        bucket_pct_f = float(bucket_pct)
    except (TypeError, ValueError):
        return None
    if mid_f <= 0 or price_f <= 0 or bucket_pct_f <= 0:
        return None
    distance_pct = abs(price_f - mid_f) / mid_f * 100.0
    bucket = round(distance_pct / bucket_pct_f)
    if bucket >= max_buckets:
        return None
    return bucket


def bucket_depth_snapshot(
    snapshot: dict,
    *,
    bucket_pct: float = DEFAULT_BUCKET_PCT,
    max_buckets: int = DEFAULT_MAX_BUCKETS,
    default_exchange: str = DEFAULT_EXCHANGE,
) -> list[dict]:
    """Convert one depth snapshot to a list of bucketed rows.

    Output schema (per row):
        exchange, symbol, side, price_bucket, quantity, order_count,
        time_bucket_ms, computed_at_ms

    Each (side, price_bucket) pair appears at most once per snapshot.
    If the snapshot has multiple top-of-book price levels that fall
    in the same bucket, the quantities are summed.
    """
    bids = snapshot.get("bids") or []
    asks = snapshot.get("asks") or []
    symbol = snapshot.get("symbol")
    if not symbol or (not bids and not asks):
        return []

    exchange = snapshot.get("exchange") or default_exchange
    mid = compute_mid_price(
        bids[0][0] if bids else None,
        asks[0][0] if asks else None,
    )
    if mid is None:
        return []

    # Time bucket: floor to the minute. heatmap uses minute resolution.
    event_time_ms = int(snapshot.get("event_time") or 0)
    time_bucket_ms = (event_time_ms // 60_000) * 60_000
    computed_at_ms = int(time.time() * 1000)

    # Accumulate quantities per (side, bucket) so multiple top-of-book
    # levels in the same bucket collapse to a single row.
    accum: dict[tuple[str, int], dict] = {}

    for side, levels in (("bid", bids), ("ask", asks)):
        for level in levels:
            # Normalize the level into a (price, qty) pair of floats
            # using a single robust coercion path. Real-world depth
            # streams hand us a few different shapes:
            #   * Binance ws depth diff: ``["100.0", "5.0"]`` (str, str)
            #   * Binance partial book:  ``[100.0, 5.0]`` (float, float)
            #   * OKX books:              ``["100.0", "5.0", "0", "2"]`` (str list)
            #   * occasional dicts:      ``{"price": ..., "qty": ...}``
            try:
                if isinstance(level, dict):
                    raw_price = level.get("price", level.get("p", level.get(0)))
                    raw_qty = level.get("qty", level.get("quantity", level.get("q", level.get(1))))
                else:
                    raw_price = level[0]
                    raw_qty = level[1]
                price = float(raw_price)
                qty = float(raw_qty)
            except (TypeError, ValueError, IndexError, KeyError):
                continue
            if qty <= 0 or price <= 0:
                continue
            bucket = price_to_bucket(price, mid, bucket_pct, max_buckets)
            if bucket is None:
                continue
            key = (side, bucket)
            if key not in accum:
                accum[key] = {
                    "exchange": exchange,
                    "symbol": symbol,
                    "side": side,
                    "price_bucket": bucket,
                    "quantity": 0.0,
                    "order_count": 0,
                }
            # Belt-and-suspenders coercion: Flink/Avro can hand us
            # nested string numerics for some exchange payloads. Force
            # float() at the merge site so a stray string in the
            # upstream record cannot turn a 0.0 accumulator into
            # `'0.0'` and break the `+=` with ``TypeError``.
            try:
                accum_qty = float(accum[key]["quantity"])
            except (TypeError, ValueError):
                accum_qty = 0.0
            try:
                addend = float(qty)
            except (TypeError, ValueError):
                continue
            accum[key]["quantity"] = accum_qty + addend
            accum[key]["order_count"] = int(accum[key].get("order_count", 0)) + 1

    out = []
    for row in accum.values():
        try:
            row["quantity"] = round(float(row["quantity"]), 8)
        except (TypeError, ValueError):
            row["quantity"] = 0.0
        row["time_bucket_ms"] = time_bucket_ms
        row["computed_at_ms"] = computed_at_ms
        out.append(row)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Flink writer
# ─────────────────────────────────────────────────────────────────────────────


class LiquidityHeatmapWriter(FlatMapFunction):
    """Flink writer that buckets depth snapshots and ships them to InfluxDB.

    Config (env-overridable):
        HEATMAP_BUCKET_PCT   default 0.1  (10 bps per bucket)
        HEATMAP_MAX_BUCKETS  default 100  (±1% around mid)
        HEATMAP_DEFAULT_EXCHANGE  default "binance"

    State:
        ``_buffer``         pending InfluxDB points (one per bucket row)
        ``_last_flush``     wall-clock of the last successful flush
        ``_known_keys``     set of (symbol, time_bucket) seen — used for
                            the "new bucket" Prometheus gauge
    """

    BATCH_SIZE = 100
    FLUSH_INTERVAL = 1.0

    def __init__(self, default_exchange: str = "binance") -> None:
        super().__init__()
        self._default_exchange = default_exchange

    def open(self, runtime_context):
        from influxdb_client import InfluxDBClient, Point, WritePrecision
        from influxdb_client.client.write_api import SYNCHRONOUS

        from common.config import (
            INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET,
        )
        from writers.metrics import (
            init_metrics, record_buffer_size, record_kafka_source,
            record_kafka_source_drop, record_kafka_source_deserialize,
            record_writer_event_time, record_writer_new_key,
        )

        self._influx = InfluxDBClient(
            url=INFLUX_URL, token=INFLUX_TOKEN,
            org=INFLUX_ORG, timeout=5_000,
        )
        self._write_api = self._influx.write_api(write_options=SYNCHRONOUS)
        self._bucket = INFLUX_BUCKET
        self._buffer: list[Point] = []
        self._last_flush = time.time()
        self._known_keys: set[tuple[str, int]] = set()
        self._record_buffer_size = record_buffer_size
        self._record_kafka_source = record_kafka_source
        self._record_drop = record_kafka_source_drop
        self._record_deserialize = record_kafka_source_deserialize
        self._record_event_time = record_writer_event_time
        self._record_new_key = record_writer_new_key
        init_metrics()

    def close(self):
        try:
            self._flush(trigger="close")
            self._write_api.close()
            self._influx.close()
        except Exception as e:
            log.error("[LiquidityHeatmap] close error: %s", e)

    def flat_map(self, value):
        from influxdb_client import Point, WritePrecision

        self._record_kafka_source(WRITER_NAME, SOURCE_TOPIC)
        try:
            snap = json.loads(value) if isinstance(value, (str, bytes)) else value
        except (TypeError, ValueError):
            self._record_drop(WRITER_NAME, SOURCE_TOPIC, "json")
            return []

        try:
            self._record_deserialize(WRITER_NAME, SOURCE_TOPIC)
            rows = bucket_depth_snapshot(
                snap,
                bucket_pct=DEFAULT_BUCKET_PCT,
                max_buckets=DEFAULT_MAX_BUCKETS,
                default_exchange=self._default_exchange,
            )
        except Exception as e:
            log.error("[LiquidityHeatmap] bucket error | symbol=%s err=%s",
                      snap.get("symbol") if isinstance(snap, dict) else "?",
                      e)
            return []

        if not rows:
            return []

        self._record_event_time(WRITER_NAME, SOURCE_TOPIC,
                                 int(snap.get("event_time") or 0))

        for r in rows:
            key = (r["symbol"], r["time_bucket_ms"])
            if key not in self._known_keys:
                self._known_keys.add(key)
                self._record_new_key(WRITER_NAME, SINK_NAME)

            p = (
                Point("liquidity_heatmap")
                .tag("exchange", r["exchange"])
                .tag("symbol", r["symbol"])
                .tag("side", r["side"])
                .tag("price_bucket", str(r["price_bucket"]))
                .field("quantity", float(r["quantity"]))
                .field("order_count", int(r["order_count"]))
                .time(r["time_bucket_ms"], WritePrecision.MS)
            )
            self._buffer.append(p)

        if (len(self._buffer) >= self.BATCH_SIZE
                or (time.time() - self._last_flush) >= self.FLUSH_INTERVAL):
            self._flush(trigger="size-or-time")
        return []

    def _flush(self, trigger: str):
        from writers.metrics import record_flush
        if not self._buffer:
            return
        n = len(self._buffer)
        self._record_buffer_size(WRITER_NAME, SINK_NAME, 0)
        start = time.monotonic()
        error_type: str | None = None
        try:
            self._write_api.write(bucket=self._bucket, record=self._buffer)
        except Exception as e:
            error_type = type(e).__name__
            log.error("[LiquidityHeatmap] flush error (%s): %s", trigger, e)
        finally:
            record_flush(
                writer=WRITER_NAME, sink=SINK_NAME,
                count=n, duration_sec=time.monotonic() - start,
                trigger=trigger, error_type=error_type,
            )
            self._buffer.clear()
            self._last_flush = time.time()


log = logging.getLogger(__name__)
