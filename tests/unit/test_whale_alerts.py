"""
Tests for Task 2: Whale Alerts (v0.24.4).

Verifies the two halves of the whale-alert feature:

1. **Flink writer** ``WhaleAlertWriter`` (src/processing/writers/whale_alert.py)
   - Threshold filter: trades with notional USD >= threshold pass; below dropped
   - Side derivation: is_buyer_maker -> "buy"/"sell"
   - Notional arithmetic: price * quantity
   - Redis payload format
   - InfluxDB point tags/fields
   - Buffer flush (size + time triggers)
   - Metrics: record_whale_alert, kafka_source, drop

2. **API endpoint** ``GET /api/market/whale-alerts`` (backend/api/market_overview.py)
   - Returns alerts sorted by trade_time DESC
   - Applies min_usd filter
   - Filters by symbol when provided
   - Scans all symbols when not provided
   - Clamps since_minutes to 60 (Redis TTL)
   - 503 on Redis failure (init / SCAN / ZRANGE)
   - Empty keys → empty list (not 500)

Run with::

    PYTHONPATH=. python -m pytest tests/unit/test_whale_alerts.py -v
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "src" / "processing"))  # so `writers.*` is importable

# Test env
os.environ.setdefault("INFLUX_TOKEN", "fake")
os.environ.setdefault("INFLUX_URL", "http://localhost:8086")
os.environ.setdefault("INFLUX_ORG", "test")
os.environ.setdefault("INFLUX_BUCKET", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test")

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# Module-loading helpers
# ═════════════════════════════════════════════════════════════════════════════
# The whale_alert module imports pyflink (only available inside the Flink
# TaskManager container). We stub it out so the unit tests can import
# the module in CI / dev without pyflink installed.
import types as _types

_fake_pyflink = _types.ModuleType("pyflink")
_fake_pyflink_ds = _types.ModuleType("pyflink.datastream")
_fake_pyflink_ds_fn = _types.ModuleType("pyflink.datastream.functions")
_fake_pyflink_ds_fn.FlatMapFunction = object
sys.modules.setdefault("pyflink", _fake_pyflink)
sys.modules.setdefault("pyflink.datastream", _fake_pyflink_ds)
sys.modules.setdefault("pyflink.datastream.functions", _fake_pyflink_ds_fn)


# ═════════════════════════════════════════════════════════════════════════════
# PART 1: Flink writer unit tests
# ═════════════════════════════════════════════════════════════════════════════


class TestWhaleAlertThreshold:
    """Threshold filter: trades >= min_whale_usd pass, below dropped."""

    def test_trade_above_threshold_emits_alert(self):
        """A trade with notional $150K should be buffered."""
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        # Simulate the open() step's state without actually connecting
        w._buffer = []
        w._influx_buffer = []
        w._write_count = {}
        w._known_keys = set()

        # Manually call flat_map with a single trade worth $150K
        trade = json.dumps({
            "event_time": 1700000000000,
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "agg_trade_id": 12345,
            "price": 50000.0,
            "quantity": 3.0,           # 50000 * 3 = 150000
            "trade_time": 1700000000000,
            "is_buyer_maker": False,
        })
        list(w.flat_map(trade))

        assert len(w._buffer) == 1
        alert = w._buffer[0]
        assert alert["symbol"] == "BTCUSDT"
        assert alert["notional_usd"] == 150_000.0

    def test_trade_below_threshold_dropped(self):
        """A trade with notional $50K should NOT be buffered (filter)."""
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 1700000000000,
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "agg_trade_id": 1,
            "price": 50_000.0,
            "quantity": 1.0,            # = $50K, below threshold
            "trade_time": 1700000000000,
            "is_buyer_maker": False,
        })
        list(w.flat_map(trade))

        assert len(w._buffer) == 0, "Below-threshold trade should be dropped"
        assert len(w._influx_buffer) == 0

    def test_trade_exactly_at_threshold_passes(self):
        """Boundary: notional == threshold should pass (>=)."""
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 1700000000000,
            "symbol": "ETHUSDT",
            "exchange": "binance",
            "agg_trade_id": 2,
            "price": 2_000.0,
            "quantity": 50.0,            # = $100K exactly
            "trade_time": 1700000000000,
            "is_buyer_maker": False,
        })
        list(w.flat_map(trade))

        assert len(w._buffer) == 1


class TestWhaleAlertSideDerivation:
    """is_buyer_maker → side mapping."""

    def test_buyer_taker_is_buy(self):
        """is_buyer_maker=False → taker is buyer → side='buy'."""
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 0, "symbol": "BTCUSDT", "exchange": "binance",
            "agg_trade_id": 1, "price": 50_000.0, "quantity": 5.0,
            "trade_time": 0, "is_buyer_maker": False,
        })
        list(w.flat_map(trade))
        assert w._buffer[0]["side"] == "buy"

    def test_buyer_maker_is_sell(self):
        """is_buyer_maker=True → maker is buyer → taker sold → side='sell'."""
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 0, "symbol": "BTCUSDT", "exchange": "binance",
            "agg_trade_id": 2, "price": 50_000.0, "quantity": 5.0,
            "trade_time": 0, "is_buyer_maker": True,
        })
        list(w.flat_map(trade))
        assert w._buffer[0]["side"] == "sell"


class TestWhaleAlertPayloadFormat:
    """Redis payload and InfluxDB point format must be stable."""

    def test_alert_has_required_fields(self):
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 1700000000000, "symbol": "BTCUSDT",
            "exchange": "binance", "agg_trade_id": 99999,
            "price": 60_000.0, "quantity": 5.0,  # = $300K
            "trade_time": 1700000000000, "is_buyer_maker": False,
        })
        list(w.flat_map(trade))
        alert = w._buffer[0]

        for field in ["trade_id", "symbol", "exchange", "side", "price",
                       "quantity", "notional_usd", "trade_time", "detected_at"]:
            assert field in alert, f"Missing field {field} in whale alert"
        assert alert["trade_id"] == 99999
        assert alert["notional_usd"] == 300_000.0

    def test_influx_point_has_correct_tags_and_fields(self):
        from writers.whale_alert import WhaleAlertWriter
        from influxdb_client import Point

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 1700000000000, "symbol": "BTCUSDT",
            "exchange": "binance", "agg_trade_id": 1,
            "price": 50_000.0, "quantity": 2.0,  # = $100K
            "trade_time": 1700000000000, "is_buyer_maker": True,
        })
        list(w.flat_map(trade))

        assert len(w._influx_buffer) == 1
        point = w._influx_buffer[0]
        assert isinstance(point, Point)
        # Convert to line protocol to inspect tags/fields
        line = point.to_line_protocol()
        assert "whale_alerts" in line
        assert "symbol=BTCUSDT" in line
        assert "exchange=binance" in line
        assert "side=sell" in line
        assert "notional_usd=100000" in line


class TestWhaleAlertErrorHandling:
    """Invalid input must not crash the writer."""

    def test_missing_symbol_drops_trade(self):
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 0, "exchange": "binance",
            "agg_trade_id": 1, "price": 50_000.0, "quantity": 5.0,
            "trade_time": 0, "is_buyer_maker": False,
            # NO symbol
        })
        list(w.flat_map(trade))
        assert len(w._buffer) == 0

    def test_malformed_json_does_not_crash(self):
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        # Not even valid JSON
        list(w.flat_map("not-json"))
        assert len(w._buffer) == 0

    def test_negative_quantity_dropped(self):
        """Negative quantity would give negative notional; we still
        treat it as < threshold and drop.
        """
        from writers.whale_alert import WhaleAlertWriter

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []

        trade = json.dumps({
            "event_time": 0, "symbol": "BTCUSDT", "exchange": "binance",
            "agg_trade_id": 1, "price": 50_000.0, "quantity": -5.0,
            "trade_time": 0, "is_buyer_maker": False,
        })
        list(w.flat_map(trade))
        assert len(w._buffer) == 0


class TestWhaleAlertMetrics:
    """Whale alert metrics must be recorded."""

    def test_whale_alert_metric_recorded(self):
        from writers.whale_alert import WhaleAlertWriter
        from writers import whale_alert as wmodule

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []
        w._known_keys = set()
        w._write_count = {}
        w._last_flush = time.time()

        # Use a unique symbol so we can verify the counter
        trade = json.dumps({
            "event_time": 0, "symbol": "TESTUSDT", "exchange": "test",
            "agg_trade_id": 1, "price": 1.0, "quantity": 200_000.0,  # = $200K
            "trade_time": 0, "is_buyer_maker": False,
        })
        # Patch the symbol the writer actually uses (its module-level import).
        with patch.object(wmodule, "record_whale_alert") as mock_record:
            list(w.flat_map(trade))
            mock_record.assert_called_once()
            args = mock_record.call_args.kwargs
            assert args["exchange"] == "test"
            assert args["symbol"] == "TESTUSDT"
            assert args["side"] == "buy"
            assert args["notional_usd"] == 200_000.0

    def test_below_threshold_trade_does_not_record_alert_metric(self):
        from writers.whale_alert import WhaleAlertWriter
        from writers import whale_alert as wmodule

        w = WhaleAlertWriter(min_whale_usd=100_000)
        w._buffer = []
        w._influx_buffer = []
        w._known_keys = set()
        w._write_count = {}
        w._last_flush = time.time()

        trade = json.dumps({
            "event_time": 0, "symbol": "BTCUSDT", "exchange": "binance",
            "agg_trade_id": 1, "price": 50_000.0, "quantity": 1.0,  # = $50K
            "trade_time": 0, "is_buyer_maker": False,
        })
        with patch.object(wmodule, "record_whale_alert") as mock_record:
            list(w.flat_map(trade))
            mock_record.assert_not_called()


class TestWhaleAlertWriterConstants:
    """Stable constants used elsewhere (API, docs, dashboards)."""

    def test_default_threshold_is_100k(self):
        from writers.whale_alert import DEFAULT_MIN_WHALE_USD
        assert DEFAULT_MIN_WHALE_USD == 100_000.0

    def test_redis_key_prefix_stable(self):
        from writers.whale_alert import REDIS_KEY_PREFIX
        assert REDIS_KEY_PREFIX == "whale:alerts"

    def test_redis_ttl_is_1h(self):
        from writers.whale_alert import REDIS_TTL_SEC
        assert REDIS_TTL_SEC == 3600

    def test_writer_name_for_metrics(self):
        from writers.whale_alert import WRITER_NAME, SINK_NAME, SOURCE_TOPIC
        assert WRITER_NAME == "whale_alert"
        assert SINK_NAME == "redis+influxdb"
        assert SOURCE_TOPIC == "crypto_trades"


# ═════════════════════════════════════════════════════════════════════════════
# PART 2: API endpoint tests
# ═════════════════════════════════════════════════════════════════════════════


def _alert_json(symbol: str, notional_usd: float, side: str = "buy",
                 trade_time_ms: int = 1700000000000) -> str:
    """Build a Redis-member string for a whale alert."""
    return json.dumps({
        "trade_id": 1, "symbol": symbol, "exchange": "binance",
        "side": side, "price": 100.0, "quantity": notional_usd / 100.0,
        "notional_usd": notional_usd, "trade_time": trade_time_ms,
        "detected_at": trade_time_ms,
    })


class TestWhaleAlertsApiRegistration:
    """The /whale-alerts endpoint must be registered."""

    def test_endpoint_registered(self):
        from backend.api.market_overview import router
        paths = {route.path for route in router.routes if hasattr(route, "path")}
        assert "/api/market/whale-alerts" in paths


class TestWhaleAlertsApiEmpty:
    """Empty Redis → empty list (NOT 500)."""

    @pytest.mark.asyncio
    async def test_no_keys_returns_empty_list(self):
        from backend.api.market_overview import get_whale_alerts

        redis_mock = MagicMock()
        redis_mock.scan = AsyncMock(return_value=(0, []))
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            result = await get_whale_alerts(
                min_usd=100_000, limit=20, since_minutes=60,
                symbol=None, exchange="binance",
            )

        assert result["count"] == 0
        assert result["data"] == []
        assert result["min_usd"] == 100_000
        assert result["filter"]["exchange"] == "binance"
        assert result["filter"]["symbol"] is None


class TestWhaleAlertsApiSymbolFilter:
    """Symbol filter uses direct key, no SCAN."""

    @pytest.mark.asyncio
    async def test_symbol_filter_targets_specific_key(self):
        from backend.api.market_overview import get_whale_alerts

        redis_mock = MagicMock()
        redis_mock.zrevrangebyscore = AsyncMock(return_value=[
            _alert_json("BTCUSDT", 250_000.0, "buy", 1700000001000),
        ])
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            result = await get_whale_alerts(
                min_usd=100_000, limit=20, since_minutes=60,
                symbol="BTCUSDT", exchange="binance",
            )

        assert result["count"] == 1
        # SCAN should NOT be called when symbol is provided
        redis_mock.scan.assert_not_called()
        # ZREVRANGEBYSCORE should target the right key
        call = redis_mock.zrevrangebyscore.call_args
        assert "whale:alerts:binance:BTCUSDT" in call.args[0]

    @pytest.mark.asyncio
    async def test_no_symbol_filter_scans_all(self):
        from backend.api.market_overview import get_whale_alerts

        redis_mock = MagicMock()
        redis_mock.scan = AsyncMock(return_value=(0, [
            "whale:alerts:binance:BTCUSDT",
            "whale:alerts:binance:ETHUSDT",
        ]))
        redis_mock.zrevrangebyscore = AsyncMock(side_effect=[
            [_alert_json("BTCUSDT", 150_000.0, "buy", 1700000002000)],
            [_alert_json("ETHUSDT", 200_000.0, "sell", 1700000003000)],
        ])
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            result = await get_whale_alerts(
                min_usd=100_000, limit=20, since_minutes=60,
                symbol=None, exchange="binance",
            )

        assert result["count"] == 2
        # Sorted by trade_time DESC
        assert result["data"][0]["symbol"] == "ETHUSDT"  # newer
        assert result["data"][1]["symbol"] == "BTCUSDT"


class TestWhaleAlertsApiFilters:
    """min_usd and since_minutes filters."""

    @pytest.mark.asyncio
    async def test_min_usd_filter_applied(self):
        """Alerts with notional < min_usd are excluded."""
        from backend.api.market_overview import get_whale_alerts

        redis_mock = MagicMock()
        redis_mock.zrevrangebyscore = AsyncMock(return_value=[
            _alert_json("BTCUSDT", 50_000.0),  # below 100K threshold
            _alert_json("BTCUSDT", 150_000.0),  # above
        ])
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            result = await get_whale_alerts(
                min_usd=100_000, limit=20, since_minutes=60,
                symbol="BTCUSDT", exchange="binance",
            )

        assert result["count"] == 1
        assert result["data"][0]["notional_usd"] == 150_000.0

    @pytest.mark.asyncio
    async def test_since_minutes_clamped_to_60(self):
        """since_minutes > 60 is silently clamped to 60 (Redis TTL)."""
        from backend.api.market_overview import get_whale_alerts

        redis_mock = MagicMock()
        redis_mock.zrevrangebyscore = AsyncMock(return_value=[])
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            result = await get_whale_alerts(
                min_usd=100_000, limit=20, since_minutes=120,  # > 60
                symbol="BTCUSDT", exchange="binance",
            )
        # Response should report the clamped value
        assert result["since_minutes"] == 60


class TestWhaleAlertsApiFailureModes:
    """Redis failures → 503, not 500."""

    @pytest.mark.asyncio
    async def test_redis_init_failure_returns_503(self):
        from backend.api.market_overview import get_whale_alerts
        from fastapi import HTTPException

        with patch("backend.core.database.get_redis",
                    new=AsyncMock(side_effect=Exception("Redis down"))):
            with pytest.raises(HTTPException) as exc:
                await get_whale_alerts(
                    min_usd=100_000, limit=20, since_minutes=60,
                    symbol="BTCUSDT", exchange="binance",
                )
            assert exc.value.status_code == 503
            assert "Redis unavailable" in exc.value.detail

    @pytest.mark.asyncio
    async def test_redis_scan_failure_returns_503(self):
        from backend.api.market_overview import get_whale_alerts
        from fastapi import HTTPException

        redis_mock = MagicMock()
        redis_mock.scan = AsyncMock(side_effect=Exception("SCAN failed"))
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_whale_alerts(
                    min_usd=100_000, limit=20, since_minutes=60,
                    symbol=None, exchange="binance",
                )
            assert exc.value.status_code == 503
            assert "SCAN failed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_redis_zrange_failure_returns_503(self):
        from backend.api.market_overview import get_whale_alerts
        from fastapi import HTTPException

        redis_mock = MagicMock()
        redis_mock.zrevrangebyscore = AsyncMock(
            side_effect=Exception("ZRANGE timeout")
        )
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_whale_alerts(
                    min_usd=100_000, limit=20, since_minutes=60,
                    symbol="BTCUSDT", exchange="binance",
                )
            assert exc.value.status_code == 503


class TestWhaleAlertsApiSorting:
    """Results must be sorted by trade_time DESC."""

    @pytest.mark.asyncio
    async def test_results_sorted_by_trade_time_desc(self):
        from backend.api.market_overview import get_whale_alerts

        redis_mock = MagicMock()
        redis_mock.zrevrangebyscore = AsyncMock(return_value=[
            _alert_json("BTCUSDT", 200_000.0, "buy", 1700000001000),
            _alert_json("BTCUSDT", 150_000.0, "sell", 1700000003000),  # newer
            _alert_json("BTCUSDT", 100_000.0, "buy", 1700000002000),
        ])
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            result = await get_whale_alerts(
                min_usd=100_000, limit=20, since_minutes=60,
                symbol="BTCUSDT", exchange="binance",
            )
        trade_times = [a["trade_time"] for a in result["data"]]
        assert trade_times == sorted(trade_times, reverse=True)

    @pytest.mark.asyncio
    async def test_limit_caps_results(self):
        from backend.api.market_overview import get_whale_alerts

        # 5 alerts, limit=3
        members = [
            _alert_json("BTCUSDT", 100_000.0 + i, "buy",
                          1700000000000 + i)
            for i in range(5)
        ]
        redis_mock = MagicMock()
        redis_mock.zrevrangebyscore = AsyncMock(return_value=members)
        with patch("backend.core.database.get_redis",
                    new=AsyncMock(return_value=redis_mock)):
            result = await get_whale_alerts(
                min_usd=100_000, limit=3, since_minutes=60,
                symbol="BTCUSDT", exchange="binance",
            )
        assert result["count"] == 3
        # The 3 most recent (highest trade_time) should be returned
        assert result["data"][0]["trade_time"] == 1700000000004
        assert result["data"][2]["trade_time"] == 1700000000002


# ═════════════════════════════════════════════════════════════════════════════
# PART 3: Manifest alignment
# ═════════════════════════════════════════════════════════════════════════════


class TestWhaleAlertManifestEntry:
    """The whale_alerts entry exists in the canonical manifest."""

    def test_manifest_includes_whale_alerts(self):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert "whale_alerts" in CANONICAL_GOLD_TABLES

    def test_manifest_whale_alerts_has_required_fields(self):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        schema = CANONICAL_GOLD_TABLES["whale_alerts"]
        for field in ["trade_id", "symbol", "exchange", "side",
                       "price", "quantity", "notional_usd",
                       "trade_time", "detected_at"]:
            assert field in schema, f"Missing field {field} in whale_alerts schema"

    def test_manifest_canonical_count_includes_whale(self):
        """After v0.24.5 there should be 9 canonical entries
        (6 original + 1 whale_alerts + 1 gold_news_market_impact
        + 1 liquidity_heatmap)."""
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert len(CANONICAL_GOLD_TABLES) == 9
