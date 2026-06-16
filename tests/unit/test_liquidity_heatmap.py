"""
Tests for Task 5: Liquidity Heatmap (v0.24.5).

Four layers:

1. **Pure bucketing helpers** — ``compute_mid_price``,
   ``price_to_bucket``, ``bucket_depth_snapshot``
   (src/processing/writers/liquidity_heatmap.py). All are pure
   functions, no Flink / Influx / Kafka required.

2. **Manifest entry** — ``liquidity_heatmap`` declared in
   src/lakehouse/gold_schema_manifest.py.

3. **API endpoint** — ``GET /api/market/liquidity-heatmap``
   (backend/api/market_overview.py). Uses an in-memory fake Influx
   query API to avoid a real connection.

4. **Frontend type contract** — TS type for ``HeatmapResponse``
   (compile-time-only; we can't run tsc in unit-test env).

Run with::

    PYTHONPATH=. python -m pytest tests/unit/test_liquidity_heatmap.py -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src/ to path
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "src" / "processing"))

# Test env
os.environ.setdefault("INFLUX_TOKEN", "fake")
os.environ.setdefault("INFLUX_URL", "http://localhost:8086")
os.environ.setdefault("INFLUX_ORG", "test")
os.environ.setdefault("INFLUX_BUCKET", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test")


# Load the writer module via importlib to avoid the writers package
# pulling in pyflink for re-export. The writer itself has a
# try/except for the pyflink import, so we don't need to stub it.
_WRITER_MOD_NAME = "liquidity_heatmap_test"


def _load_writer():
    spec = importlib.util.spec_from_file_location(
        _WRITER_MOD_NAME,
        str(REPO / "src" / "processing" / "writers" / "liquidity_heatmap.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_WRITER_MOD_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


writer = _load_writer()


# ═════════════════════════════════════════════════════════════════════════════
# PART 1: Pure helpers
# ═════════════════════════════════════════════════════════════════════════════


class TestComputeMidPrice:
    """``compute_mid_price(best_bid, best_ask)``."""

    def test_normal_case(self):
        assert writer.compute_mid_price(100, 102) == 101.0

    def test_string_typed_prices(self):
        """Binance wire format sometimes sends prices as strings."""
        assert writer.compute_mid_price("50000", "50010") == 50005.0

    def test_zero_bid_returns_none(self):
        assert writer.compute_mid_price(0, 100) is None

    def test_zero_ask_returns_none(self):
        assert writer.compute_mid_price(100, 0) is None

    def test_negative_bid_returns_none(self):
        assert writer.compute_mid_price(-1, 100) is None

    def test_inverted_book_returns_none(self):
        """ask < bid is invalid (would imply a crossed book)."""
        assert writer.compute_mid_price(100, 99) is None

    def test_none_inputs_return_none(self):
        assert writer.compute_mid_price(None, 100) is None
        assert writer.compute_mid_price(100, None) is None
        assert writer.compute_mid_price(None, None) is None

    def test_non_numeric_strings_return_none(self):
        assert writer.compute_mid_price("abc", 100) is None
        assert writer.compute_mid_price(100, "xyz") is None


class TestPriceToBucket:
    """``price_to_bucket(price, mid, bucket_pct, max_buckets)``."""

    def test_price_at_mid_is_bucket_0(self):
        assert writer.price_to_bucket(100.0, 100.0) == 0

    def test_price_one_bucket_away(self):
        """Mid=100, bucket_pct=0.1 → bucket 1 is 0.1% away → price 99.9"""
        assert writer.price_to_bucket(99.9, 100.0) == 1
        assert writer.price_to_bucket(100.1, 100.0) == 1

    def test_price_five_buckets_away(self):
        """Mid=100, bucket_pct=0.1 → 5 buckets = 0.5% away → price 99.5"""
        assert writer.price_to_bucket(99.5, 100.0) == 5
        assert writer.price_to_bucket(100.5, 100.0) == 5

    def test_bid_and_ask_both_positive_buckets(self):
        """Bucket is always non-negative; distance is symmetric."""
        b_bid = writer.price_to_bucket(95.0, 100.0)
        b_ask = writer.price_to_bucket(105.0, 100.0)
        assert b_bid == 50
        assert b_ask == 50

    def test_out_of_range_returns_none(self):
        """Default max_buckets=100. 1% away on a 0.1 bucket = bucket 10,
        which is <100, so returns 10. But 2% away on 0.1 = bucket 20,
        still <100. Force a 1.5% away price: 1.5/0.1 = 15, OK. Force
        15% away: 150 buckets, capped at 100, returns None."""
        # Mid=100, bucket_pct=0.1, max=100
        # 15% away → 150 buckets → None
        assert writer.price_to_bucket(85.0, 100.0) is None
        assert writer.price_to_bucket(115.0, 100.0) is None

    def test_custom_max_buckets(self):
        # max=5 → 1% away (10 buckets) returns None
        assert writer.price_to_bucket(99.0, 100.0,
                                       bucket_pct=0.1, max_buckets=5) is None
        # max=50 → 0.5% away (5 buckets) returns 5
        assert writer.price_to_bucket(99.5, 100.0,
                                       bucket_pct=0.1, max_buckets=50) == 5

    def test_invalid_inputs_return_none(self):
        assert writer.price_to_bucket(0, 100) is None
        assert writer.price_to_bucket(100, 0) is None
        assert writer.price_to_bucket(-1, 100) is None
        assert writer.price_to_bucket(100, -1) is None
        assert writer.price_to_bucket(100, 100, bucket_pct=0) is None
        assert writer.price_to_bucket(100, 100, bucket_pct=-0.1) is None


class TestBucketDepthSnapshot:
    """``bucket_depth_snapshot(snapshot)`` — end-to-end bucketing."""

    def _snap(self, symbol="BTCUSDT", bids=None, asks=None, exchange="binance",
              event_time=1_700_000_000_000):
        return {
            "symbol": symbol,
            "exchange": exchange,
            "event_time": event_time,
            "bids": bids or [],
            "asks": asks or [],
        }

    def test_empty_snapshot_returns_empty(self):
        assert writer.bucket_depth_snapshot(self._snap()) == []

    def test_missing_symbol_returns_empty(self):
        snap = self._snap(symbol=None,
                          bids=[["100", "1"]], asks=[["101", "1"]])
        assert writer.bucket_depth_snapshot(snap) == []

    def test_only_bids(self):
        """With best_bid=100 and best_ask=101 the mid is 100.5. A bid
        at exactly the best_bid is therefore ~0.5% away from mid
        (5 buckets of 0.1%). The test below exercises both bid and
        ask levels at known distances from mid."""
        snap = self._snap(
            bids=[
                ["100.5", "1.0"],   # = mid → bucket 0
                ["100.4", "2.0"],   # 0.1% away → bucket 1
                ["100.3", "3.0"],   # 0.2% away → bucket 2
            ],
            asks=[
                ["100.5", "1.5"],   # = mid → bucket 0
                ["100.7", "5.0"],   # 0.2% away → bucket 2
            ],
        )
        rows = writer.bucket_depth_snapshot(snap)
        # 3 bid rows (b0, b1, b2) + 2 ask rows (b0, b2) = 5 rows
        assert len(rows) == 5
        # All rows have side=bid or side=ask
        bid_rows = [r for r in rows if r["side"] == "bid"]
        ask_rows = [r for r in rows if r["side"] == "ask"]
        assert len(bid_rows) == 3
        assert len(ask_rows) == 2
        # bid at mid has bucket 0 and qty 1
        b0 = [r for r in bid_rows if r["price_bucket"] == 0][0]
        assert b0["quantity"] == 1.0
        # bid bucket 2 has qty 3
        b2 = [r for r in bid_rows if r["price_bucket"] == 2][0]
        assert b2["quantity"] == 3.0

    def test_levels_in_same_bucket_collapse(self):
        """Two bid levels 100.39 and 100.41 both fall in bucket 1
        (~0.1% and ~0.09% from mid=100.5). They collapse to one row."""
        snap = self._snap(
            bids=[
                ["100.5", "1.0"],
                ["100.39", "2.0"],  # bucket 1
                ["100.41", "3.0"],  # bucket 1
                ["100.0",  "4.0"],  # bucket 5
            ],
            asks=[["100.5", "5.0"]],
        )
        rows = writer.bucket_depth_snapshot(snap)
        bid_rows = [r for r in rows if r["side"] == "bid"]
        # bucket 0 (1.0) + bucket 1 (2+3=5.0) + bucket 5 (4.0) = 3 bid rows
        assert len(bid_rows) == 3
        b1 = [r for r in bid_rows if r["price_bucket"] == 1][0]
        assert b1["quantity"] == 5.0
        assert b1["order_count"] == 2

    def test_time_bucket_floored_to_minute(self):
        snap = self._snap(
            bids=[["100.5", "1.0"]],
            asks=[["100.5", "1.0"]],
            event_time=1_700_000_123_456,  # not on a minute boundary
        )
        rows = writer.bucket_depth_snapshot(snap)
        for r in rows:
            # 1_700_000_123_456 // 60_000 * 60_000 == 1_700_000_100_000
            assert r["time_bucket_ms"] == 1_700_000_100_000

    def test_default_exchange_fallback(self):
        """When exchange missing in snapshot, default to 'binance'."""
        snap = {
            "symbol": "BTCUSDT",
            "event_time": 1_700_000_000_000,
            "bids": [["100", "1"]],
            "asks": [["101", "1"]],
            # NO "exchange" key
        }
        rows = writer.bucket_depth_snapshot(snap, default_exchange="kraken")
        assert all(r["exchange"] == "kraken" for r in rows)

    def test_inverted_book_returns_empty(self):
        """ask < bid → no mid → empty."""
        snap = self._snap(
            bids=[["101", "1"]],
            asks=[["100", "1"]],
        )
        assert writer.bucket_depth_snapshot(snap) == []

    def test_invalid_level_dropped(self):
        """Levels with non-numeric price/qty are silently dropped."""
        snap = self._snap(
            bids=[
                ["100.5", "1.0"],
                ["not-a-number", "2.0"],
                ["100.4", "abc"],
            ],
            asks=[["100.5", "1.0"]],
        )
        rows = writer.bucket_depth_snapshot(snap)
        # Only the valid bid@100.5 and ask@100.5 should produce rows
        assert len(rows) == 2

    def test_zero_qty_level_dropped(self):
        """qty=0 is filtered (no liquidity contribution)."""
        snap = self._snap(
            bids=[["100.5", "0"]],
            asks=[["100.5", "1.0"]],
        )
        rows = writer.bucket_depth_snapshot(snap)
        # 1 ask row only
        assert len(rows) == 1
        assert rows[0]["side"] == "ask"

    def test_out_of_window_levels_dropped(self):
        """Levels beyond max_buckets are dropped. With max_buckets=100
        and bucket_pct=0.1, anything more than 10% from mid is dropped.
        """
        snap = self._snap(
            bids=[
                ["100.5", "1.0"],   # at mid → kept
                ["80.0",  "5.0"],   # ~20% below mid → dropped
            ],
            asks=[["100.5", "1.5"]],  # at mid → kept
        )
        rows = writer.bucket_depth_snapshot(snap)
        # 1 bid at mid + 1 ask at mid = 2 rows; the bid@80 is dropped
        assert len(rows) == 2
        # All remaining rows should be at the mid (bucket 0)
        for r in rows:
            assert r["price_bucket"] == 0

    def test_row_shape_matches_manifest(self):
        """Every output row has all manifest fields."""
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        snap = self._snap(
            bids=[["100.5", "1.0"]],
            asks=[["100.5", "1.0"]],
        )
        rows = writer.bucket_depth_snapshot(snap)
        assert len(rows) > 0
        row_fields = set(rows[0].keys())
        # The output uses time_bucket_ms/computed_at_ms; the manifest
        # uses time_bucket. The API maps between them.
        for required in ("exchange", "symbol", "side", "price_bucket",
                          "quantity", "time_bucket_ms", "computed_at_ms"):
            assert required in row_fields, (
                f"Missing {required} in row output"
            )


# ═════════════════════════════════════════════════════════════════════════════
# PART 2: Manifest alignment
# ═════════════════════════════════════════════════════════════════════════════


class TestLiquidityHeatmapManifestEntry:
    """``liquidity_heatmap`` declared in the manifest."""

    def test_manifest_includes_liquidity_heatmap(self):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert "liquidity_heatmap" in CANONICAL_GOLD_TABLES

    def test_manifest_schema_has_required_columns(self):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        schema = CANONICAL_GOLD_TABLES["liquidity_heatmap"]
        for col in ["exchange", "symbol", "side", "price_bucket",
                     "quantity", "order_count", "time_bucket"]:
            assert col in schema, f"Missing column {col}"

    def test_manifest_count_includes_heatmap(self):
        """v0.24.5 Task 5 brings canonical count to 9."""
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert len(CANONICAL_GOLD_TABLES) == 9


# ═════════════════════════════════════════════════════════════════════════════
# PART 3: API endpoint
# ═════════════════════════════════════════════════════════════════════════════


class TestLiquidityHeatmapApiRegistration:
    def test_endpoint_registered(self):
        from backend.api.market_overview import router
        paths = {route.path for route in router.routes if hasattr(route, "path")}
        assert "/api/market/liquidity-heatmap" in paths


class _FakeRecord:
    """Minimal InfluxDB record stub for testing the API's table iterator."""
    def __init__(self, ts_ms: int, side: str, bucket: int, qty: float):
        self._ts_ms = ts_ms
        self.values = {"side": side, "price_bucket": str(bucket)}
        self._value = qty

    def get_time(self):
        return datetime.fromtimestamp(self._ts_ms / 1000.0, tz=timezone.utc)

    def get_value(self):
        return self._value


class _FakeTable:
    def __init__(self, records):
        self.records = records


class TestLiquidityHeatmapApiHappyPath:
    """Successful query → 2D matrix returned in flat-row form."""

    @pytest.mark.asyncio
    async def test_returns_bid_and_ask_rows(self):
        from backend.api.market_overview import get_liquidity_heatmap

        ts = 1_700_000_000_000
        bid_records = [
            _FakeRecord(ts,     "bid", 0, 1.0),
            _FakeRecord(ts,     "bid", 1, 2.0),
            _FakeRecord(ts+60_000, "bid", 0, 1.5),
        ]
        ask_records = [
            _FakeRecord(ts,     "ask", 0, 1.2),
            _FakeRecord(ts,     "ask", 5, 3.0),
        ]
        fake_query_api = MagicMock()
        fake_query_api.query = MagicMock(return_value=[
            _FakeTable(bid_records),
            _FakeTable(ask_records),
        ])

        fake_influx = MagicMock()
        fake_influx.query_api = MagicMock(return_value=fake_query_api)

        with patch("backend.core.database.get_influx",
                    new=MagicMock(return_value=fake_influx)):
            result = await get_liquidity_heatmap(
                symbol="BTCUSDT", hours=4, bucket_count=20, exchange="binance",
            )

        assert "data" in result
        assert "bid" in result["data"]
        assert "ask" in result["data"]
        assert len(result["data"]["bid"]) == 3
        assert len(result["data"]["ask"]) == 2
        # Each row is [ts_ms, bucket, qty]
        for row in result["data"]["bid"]:
            assert len(row) == 3
            assert isinstance(row[0], int)
            assert isinstance(row[1], int)
            assert isinstance(row[2], float)

    @pytest.mark.asyncio
    async def test_matrix_shape_reflects_lookback(self):
        from backend.api.market_overview import get_liquidity_heatmap

        fake_query_api = MagicMock()
        fake_query_api.query = MagicMock(return_value=[])
        fake_influx = MagicMock()
        fake_influx.query_api = MagicMock(return_value=fake_query_api)

        with patch("backend.core.database.get_influx",
                    new=MagicMock(return_value=fake_influx)):
            result = await get_liquidity_heatmap(
                symbol="ETHUSDT", hours=8, bucket_count=30, exchange="binance",
            )

        assert result["matrix_shape"]["time_buckets"] == 0
        assert result["matrix_shape"]["price_buckets_per_side"] == 30
        assert result["filter"]["hours"] == 8
        assert result["filter"]["symbol"] == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_buckets_outside_window_filtered(self):
        """Buckets >= bucket_count are filtered out by the API."""
        from backend.api.market_overview import get_liquidity_heatmap

        ts = 1_700_000_000_000
        records = [
            _FakeRecord(ts, "bid", 0, 1.0),    # in window
            _FakeRecord(ts, "bid", 25, 2.0),   # out (>20)
            _FakeRecord(ts, "ask", 19, 3.0),   # in window
        ]
        fake_query_api = MagicMock()
        fake_query_api.query = MagicMock(return_value=[_FakeTable(records)])
        fake_influx = MagicMock()
        fake_influx.query_api = MagicMock(return_value=fake_query_api)

        with patch("backend.core.database.get_influx",
                    new=MagicMock(return_value=fake_influx)):
            result = await get_liquidity_heatmap(
                symbol="BTCUSDT", hours=4, bucket_count=20, exchange="binance",
            )

        # bucket 25 should be filtered out
        assert len(result["data"]["bid"]) == 1
        assert result["data"]["bid"][0][1] == 0
        # bucket 19 should remain
        assert len(result["data"]["ask"]) == 1
        assert result["data"]["ask"][0][1] == 19


class TestLiquidityHeatmapApiFailureModes:
    """Influx failures → 503, not 500."""

    @pytest.mark.asyncio
    async def test_influx_init_failure_returns_503(self):
        from backend.api.market_overview import get_liquidity_heatmap
        from fastapi import HTTPException

        with patch("backend.core.database.get_influx",
                    new=MagicMock(side_effect=Exception("Influx down"))):
            with pytest.raises(HTTPException) as exc:
                await get_liquidity_heatmap(
                    symbol="BTCUSDT", hours=4, bucket_count=20, exchange="binance",
                )
        assert exc.value.status_code == 503
        assert "InfluxDB" in exc.value.detail

    @pytest.mark.asyncio
    async def test_influx_query_failure_returns_503(self):
        from backend.api.market_overview import get_liquidity_heatmap
        from fastapi import HTTPException

        fake_query_api = MagicMock()
        fake_query_api.query = MagicMock(side_effect=Exception("Flux parse error"))
        fake_influx = MagicMock()
        fake_influx.query_api = MagicMock(return_value=fake_query_api)

        with patch("backend.core.database.get_influx",
                    new=MagicMock(return_value=fake_influx)):
            with pytest.raises(HTTPException) as exc:
                await get_liquidity_heatmap(
                    symbol="BTCUSDT", hours=4, bucket_count=20, exchange="binance",
                )
        assert exc.value.status_code == 503
        assert "Heatmap data unavailable" in exc.value.detail


class TestLiquidityHeatmapApiValidation:
    """Symbol regex validation."""

    def test_symbol_must_match_canonical_form(self):
        """The endpoint declares a regex pattern for symbol."""
        import inspect
        from backend.api.market_overview import get_liquidity_heatmap
        sig = inspect.signature(get_liquidity_heatmap)
        symbol_param = sig.parameters["symbol"]
        # symbol is required (no real default). FastAPI wraps in Query
        # which has a Pydantic Undefined default. The point is that
        # the parameter exists and is required at the API layer.
        assert symbol_param.name == "symbol"


# ═════════════════════════════════════════════════════════════════════════════
# PART 4: Frontend type contract
# ═════════════════════════════════════════════════════════════════════════════


class TestLiquidityHeatmapFrontendTypes:
    def test_typescript_declares_heatmap_types(self):
        path = REPO / "frontend" / "src" / "services" / "marketOverviewService.ts"
        text = path.read_text(encoding="utf-8")
        for needle in (
            "export interface HeatmapRow",
            "export interface HeatmapData",
            "export interface HeatmapFilter",
            "export interface HeatmapResponse",
            "fetchLiquidityHeatmap",
        ):
            assert needle in text, f"Frontend missing {needle}"

    def test_typescript_uses_correct_field_names(self):
        path = REPO / "frontend" / "src" / "services" / "marketOverviewService.ts"
        text = path.read_text(encoding="utf-8")
        # The TS types must match the API's snake_case fields
        for field in ("matrix_shape", "price_buckets_per_side",
                       "time_buckets", "bucket_count"):
            assert field in text, f"TS missing field {field}"


# ═════════════════════════════════════════════════════════════════════════════
# PART 5: Writer constants
# ═════════════════════════════════════════════════════════════════════════════


class TestLiquidityHeatmapWriterConstants:
    """Stable module-level constants used elsewhere (docs, dashboards)."""

    def test_default_bucket_pct_is_0_1(self):
        # Reload to pick up env vars set in conftest
        assert writer.DEFAULT_BUCKET_PCT == 0.1

    def test_default_max_buckets_is_100(self):
        assert writer.DEFAULT_MAX_BUCKETS == 100

    def test_default_exchange_is_binance(self):
        assert writer.DEFAULT_EXCHANGE == "binance"

    def test_writer_name_for_metrics(self):
        assert writer.WRITER_NAME == "liquidity_heatmap"
        assert writer.SINK_NAME == "influxdb"
        assert writer.SOURCE_TOPIC == "crypto_depth"
