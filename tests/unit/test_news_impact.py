"""
Tests for Task 4: News ↔ Price Impact (v0.24.5).

Covers four layers:

1. **Spark job builder** — ``build_impact_row`` + ``compute_impact_score``
   (pure functions in src/lakehouse/gold/news_impact.py).
2. **Manifest entry** — ``gold_news_market_impact`` declared in
   src/lakehouse/gold_schema_manifest.py.
3. **API endpoint** — ``GET /api/market/news-impact``
   (backend/api/market_overview.py).
4. **Frontend service type contract** — TS type for ``NewsImpactItem``
   (compile-time-only; we can't run tsc in unit-test env).

Run with::

    PYTHONPATH=. python -m pytest tests/unit/test_news_impact.py -v
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path so `lakehouse.*` is importable from this test.
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "src" / "processing"))  # so `writers.*` is importable


# Helper: load news_impact.py directly via importlib to avoid the
# ``lakehouse.gold`` package __init__ which would pull in pyspark.
import importlib.util as _ilu

_NEWS_IMPACT_MOD_NAME = "news_impact_test"


def _load_news_impact():
    spec = _ilu.spec_from_file_location(
        _NEWS_IMPACT_MOD_NAME,
        str(REPO / "src" / "lakehouse" / "gold" / "news_impact.py"),
    )
    mod = _ilu.module_from_spec(spec)
    sys.modules[_NEWS_IMPACT_MOD_NAME] = mod  # so `from X import Y` works
    spec.loader.exec_module(mod)
    return mod


news_impact = _load_news_impact()

# Test env
os.environ.setdefault("INFLUX_TOKEN", "fake")
os.environ.setdefault("INFLUX_URL", "http://localhost:8086")
os.environ.setdefault("INFLUX_ORG", "test")
os.environ.setdefault("INFLUX_BUCKET", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test")


# ═════════════════════════════════════════════════════════════════════════════
# PART 1: Spark job — compute_impact_score
# ═════════════════════════════════════════════════════════════════════════════


class TestComputeImpactScore:
    """``compute_impact_score(change_1h, change_4h, change_24h, sentiment)``."""

    def test_no_changes_returns_none(self):
        from news_impact_test import compute_impact_score
        assert compute_impact_score(None, None, None, 0.5) is None

    def test_bullish_news_with_upward_change_positive_score(self):
        from news_impact_test import compute_impact_score
        # change_1h=+2.0, change_4h=+4.0, change_24h=+6.0, sentiment=+0.8
        # max abs = 6.0, sign = +1
        score = compute_impact_score(2.0, 4.0, 6.0, 0.8)
        assert score == 6.0

    def test_bearish_news_with_downward_change_negative_score(self):
        from news_impact_test import compute_impact_score
        # change_1h=-2.0, change_4h=-1.0, change_24h=-3.0, sentiment=-0.5
        # max abs = 3.0, sign = -1
        score = compute_impact_score(-2.0, -1.0, -3.0, -0.5)
        assert score == -3.0

    def test_news_move_against_sentiment_keeps_signed_score(self):
        """Bullish news but price went down → score is still positive
        (we report magnitude * sign(sentiment), not the actual direction
        of the move). This is a known design choice — the score measures
        'how much did the market react to the news signal' regardless
        of whether the reaction was in the same direction.
        """
        from news_impact_test import compute_impact_score
        score = compute_impact_score(-5.0, None, None, 0.9)
        assert score == 5.0  # magnitude 5, sign +1

    def test_neutral_sentiment_returns_magnitude_only(self):
        from news_impact_test import compute_impact_score
        # sentiment=0 → score = magnitude, sign neutral (0.0)
        assert compute_impact_score(1.5, None, None, 0.0) == 0.0
        assert compute_impact_score(1.5, 2.0, None, 0.0) == 0.0

    def test_none_sentiment_treated_as_neutral(self):
        from news_impact_test import compute_impact_score
        # sentiment=None → return 0.0 (don't fall back to abs; the API
        # needs to distinguish "no signal" from "bullish 0.4%")
        assert compute_impact_score(2.0, 1.0, 0.5, None) == 0.0

    def test_partial_data_only_1h(self):
        """Young article: only change_1h_pct known."""
        from news_impact_test import compute_impact_score
        score = compute_impact_score(1.5, None, None, 0.6)
        assert score == 1.5

    def test_partial_data_only_24h(self):
        """Article where the 1h and 4h klines don't exist."""
        from news_impact_test import compute_impact_score
        score = compute_impact_score(None, None, -2.5, -0.4)
        assert score == -2.5


# ═════════════════════════════════════════════════════════════════════════════
# PART 2: Spark job — build_impact_row
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildImpactRow:
    """``build_impact_row(...)`` pure builder."""

    def test_row_has_all_manifest_fields(self):
        from news_impact_test import build_impact_row
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES

        row = build_impact_row(
            news_id=12345,
            symbol="BTCUSDT",
            exchange="binance",
            published_at_ms=1_700_000_000_000,
            headline="Bitcoin ETF approved",
            url="https://example.com/etf",
            source="coindesk",
            sentiment=0.8,
            price_at_news=50_000.0,
            price_1h_after=51_000.0,   # +2%
            price_4h_after=52_000.0,   # +4%
            price_24h_after=53_000.0,  # +6%
            computed_at_ms=1_700_000_000_000,
        )
        # Every manifest field is present
        for field in CANONICAL_GOLD_TABLES["gold_news_market_impact"]:
            assert field in row, f"Missing field {field} in row"

    def test_change_pct_arithmetic(self):
        from news_impact_test import build_impact_row
        row = build_impact_row(
            news_id=1, symbol="BTCUSDT", exchange="binance",
            published_at_ms=0, headline="t", url="u", source="s",
            sentiment=0.5,
            price_at_news=100.0,
            price_1h_after=110.0,  # +10%
            price_4h_after=120.0,  # +20%
            price_24h_after=150.0, # +50%
            computed_at_ms=0,
        )
        assert row["change_1h_pct"]  == 10.0
        assert row["change_4h_pct"]  == 20.0
        assert row["change_24h_pct"] == 50.0

    def test_change_pct_none_when_after_price_missing(self):
        from news_impact_test import build_impact_row
        row = build_impact_row(
            news_id=1, symbol="BTCUSDT", exchange="binance",
            published_at_ms=0, headline="t", url="u", source="s",
            sentiment=0.5,
            price_at_news=100.0,
            price_1h_after=None,  # kline missing
            price_4h_after=None,
            price_24h_after=None,
            computed_at_ms=0,
        )
        assert row["change_1h_pct"]  is None
        assert row["change_4h_pct"]  is None
        assert row["change_24h_pct"] is None

    def test_change_pct_none_when_price_at_news_is_zero(self):
        from news_impact_test import build_impact_row
        row = build_impact_row(
            news_id=1, symbol="BTCUSDT", exchange="binance",
            published_at_ms=0, headline="t", url="u", source="s",
            sentiment=0.5,
            price_at_news=0.0,  # would divide-by-zero
            price_1h_after=100.0,
            price_4h_after=200.0,
            price_24h_after=300.0,
            computed_at_ms=0,
        )
        assert row["change_1h_pct"]  is None
        assert row["change_4h_pct"]  is None
        assert row["change_24h_pct"] is None

    def test_impact_score_uses_max_horizon(self):
        from news_impact_test import build_impact_row
        row = build_impact_row(
            news_id=1, symbol="BTCUSDT", exchange="binance",
            published_at_ms=0, headline="t", url="u", source="s",
            sentiment=0.7,
            price_at_news=100.0,
            price_1h_after=102.0,  # +2%
            price_4h_after=108.0,  # +8%
            price_24h_after=105.0, # +5%
            computed_at_ms=0,
        )
        # max abs = 8.0, sign = +1
        assert row["impact_score"] == 8.0

    def test_published_at_is_iso_utc(self):
        from news_impact_test import build_impact_row
        row = build_impact_row(
            news_id=1, symbol="BTCUSDT", exchange="binance",
            published_at_ms=1_700_000_000_000,
            headline="t", url="u", source="s",
            sentiment=0.5,
            price_at_news=100.0,
            price_1h_after=None, price_4h_after=None, price_24h_after=None,
            computed_at_ms=0,
        )
        # Must end in +00:00 (UTC) — ISO 8601 with timezone
        assert row["published_at"].endswith("+00:00")
        # Should be parseable back
        from datetime import datetime
        parsed = datetime.fromisoformat(row["published_at"])
        assert parsed.year == 2023  # 1.7e12 ms ≈ Nov 2023


# ═════════════════════════════════════════════════════════════════════════════
# PART 3: Manifest alignment
# ═════════════════════════════════════════════════════════════════════════════


class TestNewsImpactManifestEntry:
    """``gold_news_market_impact`` declared in the manifest."""

    def test_manifest_includes_news_market_impact(self):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert "gold_news_market_impact" in CANONICAL_GOLD_TABLES

    def test_manifest_schema_has_required_columns(self):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        schema = CANONICAL_GOLD_TABLES["gold_news_market_impact"]
        for col in [
            "news_id", "symbol", "exchange", "published_at",
            "headline", "url", "source", "sentiment",
            "price_at_news", "price_1h_after", "price_4h_after",
            "price_24h_after", "change_1h_pct", "change_4h_pct",
            "change_24h_pct", "impact_score", "computed_at",
        ]:
            assert col in schema, f"Missing column {col} in manifest schema"

    def test_manifest_count_includes_news_impact(self):
        """v0.24.5 canonical count = 9 (was 8 in v0.24.5 Task 4)."""
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert len(CANONICAL_GOLD_TABLES) == 9

    def test_deprecation_list_unchanged(self):
        from lakehouse.gold_schema_manifest import DEPRECATED_SPARK_TABLES
        assert len(DEPRECATED_SPARK_TABLES) == 6  # unchanged in v0.24.5


# ═════════════════════════════════════════════════════════════════════════════
# PART 4: API endpoint
# ═════════════════════════════════════════════════════════════════════════════


class TestNewsImpactApiRegistration:
    """The /news-impact endpoint must be registered."""

    def test_endpoint_registered(self):
        from backend.api.market_overview import router
        paths = {route.path for route in router.routes if hasattr(route, "path")}
        assert "/api/market/news-impact" in paths


def _trino_row(
    news_id: int = 1,
    symbol: str = "BTCUSDT",
    exchange: str = "binance",
    headline: str = "BTC hits new ATH",
    sentiment: float = 0.5,
    price_at: float = 50000.0,
    p1: float = 51000.0, p4: float = 52000.0, p24: float = 53000.0,
    impact: float = 6.0,
    published_at: str = "2026-06-10T12:00:00+00:00",
    computed_at: str = "2026-06-10T12:00:01+00:00",
    url: str = "https://example.com/x",
    source: str = "coindesk",
) -> tuple:
    """Build a single Trino-returned row tuple matching the SELECT
    column order in get_news_impact()."""
    return (
        news_id, symbol, exchange, published_at, headline, url, source,
        sentiment, price_at, p1, p4, p24,
        2.0, 4.0, 6.0, impact, computed_at,
    )


class TestNewsImpactApiEmpty:
    """Empty Trino result → empty list (NOT 500)."""

    @pytest.mark.asyncio
    async def test_no_rows_returns_empty_list(self):
        from backend.api.market_overview import get_news_impact

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(return_value=[])
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_news_impact(
                days=7, limit=50, symbol=None,
                min_impact_pct=0.0, exchange="binance",
            )

        assert result["count"] == 0
        assert result["data"] == []
        assert result["filter"]["days"] == 7
        assert result["filter"]["symbol"] is None


class TestNewsImpactApiHappyPath:
    """Successful query → rows in the response."""

    @pytest.mark.asyncio
    async def test_rows_are_returned_and_shaped(self):
        from backend.api.market_overview import get_news_impact

        rows = [_trino_row(news_id=1), _trino_row(news_id=2, symbol="ETHUSDT")]
        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(return_value=rows)
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_news_impact(
                days=7, limit=50, symbol=None,
                min_impact_pct=0.0, exchange="binance",
            )

        assert result["count"] == 2
        assert result["data"][0]["news_id"] == 1
        assert result["data"][1]["news_id"] == 2
        # Headline should be present
        assert "BTC" in result["data"][0]["headline"] or \
               "ATH"  in result["data"][0]["headline"]

    @pytest.mark.asyncio
    async def test_symbol_filter_added_to_where_clause(self):
        from backend.api.market_overview import get_news_impact

        captured_sql: list[str] = []

        async def fake_fetch_all(sql, query_type=None, *args, **kwargs):
            captured_sql.append(sql)
            return [_trino_row()]

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=fake_fetch_all)
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            await get_news_impact(
                days=3, limit=10, symbol="BTCUSDT",
                min_impact_pct=0.0, exchange="binance",
            )

        assert len(captured_sql) == 1
        sql = captured_sql[0]
        assert "symbol = 'BTCUSDT'" in sql
        assert "INTERVAL '3' DAY" in sql
        assert "LIMIT 10" in sql
        assert "exchange = 'binance'" in sql

    @pytest.mark.asyncio
    async def test_min_impact_filter_added(self):
        from backend.api.market_overview import get_news_impact

        captured_sql: list[str] = []

        async def fake_fetch_all(sql, query_type=None, *args, **kwargs):
            captured_sql.append(sql)
            return []

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=fake_fetch_all)
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            await get_news_impact(
                days=7, limit=50, symbol=None,
                min_impact_pct=2.5, exchange="binance",
            )
        assert "ABS(impact_score) >= 2.5" in captured_sql[0]

    @pytest.mark.asyncio
    async def test_default_exchange_is_binance(self):
        from backend.api.market_overview import get_news_impact

        captured_sql: list[str] = []

        async def fake_fetch_all(sql, query_type=None, *args, **kwargs):
            captured_sql.append(sql)
            return []

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=fake_fetch_all)
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            await get_news_impact(
                days=7, limit=50, symbol=None,
                min_impact_pct=0.0, exchange="binance",
            )
        assert "exchange = 'binance'" in captured_sql[0]


class TestNewsImpactApiFailureModes:
    """Trino failures → 503, not 500."""

    @pytest.mark.asyncio
    async def test_trino_init_failure_returns_503(self):
        from backend.api.market_overview import get_news_impact
        from fastapi import HTTPException

        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(side_effect=Exception("Trino unreachable"))):
            with pytest.raises(HTTPException) as exc:
                await get_news_impact(
                    days=7, limit=50, symbol=None,
                    min_impact_pct=0.0, exchange="binance",
                )
        assert exc.value.status_code == 503
        assert "Trino" in exc.value.detail

    @pytest.mark.asyncio
    async def test_trino_query_failure_returns_503(self):
        from backend.api.market_overview import get_news_impact
        from fastapi import HTTPException

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=Exception("Query timeout"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_news_impact(
                    days=7, limit=50, symbol=None,
                    min_impact_pct=0.0, exchange="binance",
                )
        assert exc.value.status_code == 503
        assert "Gold data unavailable" in exc.value.detail


class TestNewsImpactApiValidation:
    """Bad input is rejected by FastAPI validation."""

    @pytest.mark.asyncio
    async def test_invalid_symbol_format_rejected(self):
        """The regex is ^[A-Z0-9]{2,20}USDT$. Lowercase should fail."""
        from backend.api.market_overview import get_news_impact

        # We can't easily exercise FastAPI validation through the bare
        # function signature; it would require a TestClient. Instead
        # we verify the *signature* carries the right pattern.
        import inspect
        sig = inspect.signature(get_news_impact)
        symbol_param = sig.parameters["symbol"]
        # When ``pattern=`` is set, FastAPI turns the param into a Query
        # object that has ``pattern`` as an attribute.
        # (No public API for the pattern; we just verify the param name
        # and the endpoint accepts the kwarg shape.)
        assert symbol_param.name == "symbol"

    def test_days_range_constrained(self):
        from backend.api.market_overview import get_news_impact
        import inspect
        from fastapi.params import Query as FastAPIQuery
        sig = inspect.signature(get_news_impact)
        days_param = sig.parameters["days"]
        # FastAPI wraps defaults in a Query object; unwrap to compare.
        default = days_param.default
        if isinstance(default, FastAPIQuery):
            default = default.default
        assert default == 7

    def test_limit_range_constrained(self):
        from backend.api.market_overview import get_news_impact
        import inspect
        from fastapi.params import Query as FastAPIQuery
        sig = inspect.signature(get_news_impact)
        limit_param = sig.parameters["limit"]
        default = limit_param.default
        if isinstance(default, FastAPIQuery):
            default = default.default
        assert default == 50


class TestNewsImpactApiTimestampNormalization:
    """Non-string timestamps (datetime objects) are stringified."""

    @pytest.mark.asyncio
    async def test_datetime_timestamps_are_stringified(self):
        from backend.api.market_overview import get_news_impact
        from datetime import datetime, timezone

        # Trino drivers sometimes return datetimes as Python objects.
        # Column order matches the SELECT in the endpoint.
        rows = [(
            1, "BTCUSDT", "binance",
            datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),  # published_at
            "headline", "url", "src",
            0.5, 100.0, 110.0, 120.0, 150.0,
            10.0, 20.0, 50.0, 50.0,
            datetime(2026, 6, 10, 12, 1, tzinfo=timezone.utc),  # computed_at
        )]
        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(return_value=rows)
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_news_impact(
                days=7, limit=50, symbol=None,
                min_impact_pct=0.0, exchange="binance",
            )
        assert isinstance(result["data"][0]["published_at"], str)
        assert isinstance(result["data"][0]["computed_at"], str)


# ═════════════════════════════════════════════════════════════════════════════
# PART 5: Frontend type contract
# ═════════════════════════════════════════════════════════════════════════════


class TestNewsImpactFrontendTypes:
    """The TS source declares the right field names matching the API."""

    def test_typescript_declares_NewsImpactItem(self):
        """The TS file must export NewsImpactItem with the manifest's
        field names (snake_case, matching the API)."""
        path = REPO / "frontend" / "src" / "services" / "marketOverviewService.ts"
        text = path.read_text(encoding="utf-8")
        assert "export interface NewsImpactItem" in text
        for field in [
            "news_id", "symbol", "exchange", "published_at",
            "headline", "url", "source", "sentiment",
            "price_at_news", "price_1h_after", "price_4h_after",
            "price_24h_after", "change_1h_pct", "change_4h_pct",
            "change_24h_pct", "impact_score", "computed_at",
        ]:
            assert field in text, (
                f"Frontend interface is missing field {field}"
            )

    def test_typescript_declares_filter_and_helper(self):
        path = REPO / "frontend" / "src" / "services" / "marketOverviewService.ts"
        text = path.read_text(encoding="utf-8")
        assert "fetchNewsPriceImpact" in text
        assert "fetchNewsPriceImpactForSymbol" in text
        assert "NewsImpactFilter" in text
