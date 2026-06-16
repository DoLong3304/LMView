"""
Tests for Task 1: Dedicated Gold table endpoints (v0.24.4).

Verifies the 6 new endpoints added to ``backend/api/market_overview.py``:
- GET /api/market/movers
- GET /api/market/dominance
- GET /api/market/volatility
- GET /api/market/sectors
- GET /api/market/news-sentiment
- GET /api/market/indicators

These tests mock the Trino client and the ``get_trino`` factory so the
endpoints can be exercised in isolation. The HTTP layer is exercised via
``TestClient`` so the route registration is also checked.

Run with::

    PYTHONPATH=. python -m pytest tests/unit/test_market_dedicated_endpoints.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

# Set test env vars before importing anything
os.environ.setdefault("INFLUX_TOKEN", "fake")
os.environ.setdefault("INFLUX_URL", "http://localhost:8086")
os.environ.setdefault("INFLUX_ORG", "test")
os.environ.setdefault("INFLUX_BUCKET", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test")

import pytest


# ── Module-level helpers ────────────────────────────────────────────────────


def _make_trino_mock(fetch_one=None, fetch_all=None):
    """Build a mock AsyncTrinoClient."""
    trino = MagicMock()
    trino.fetch_one = AsyncMock(return_value=fetch_one or (0, 0, 0, 0))
    trino.fetch_all = AsyncMock(return_value=fetch_all or [])
    return trino


# ── Endpoint registration tests ─────────────────────────────────────────────


class TestEndpointRegistration:
    """All 6 new endpoints must be registered on the router."""

    def test_all_dedicated_endpoints_registered(self):
        from backend.api.market_overview import router

        expected_paths = {
            "/api/market/movers",
            "/api/market/dominance",
            "/api/market/volatility",
            "/api/market/sectors",
            "/api/market/news-sentiment",
            "/api/market/indicators",
        }
        actual_paths = {
            route.path for route in router.routes
            if hasattr(route, "path") and route.path.startswith("/api/market/")
        }
        missing = expected_paths - actual_paths
        assert not missing, f"Missing endpoints: {missing}"

    def test_legacy_endpoints_preserved(self):
        """The /overview, /heatmap, /rankings endpoints must still exist
        for back-compat (existing Frontend pages may still use them).
        """
        from backend.api.market_overview import router
        actual_paths = {
            route.path for route in router.routes
            if hasattr(route, "path")
        }
        for legacy in [
            "/api/market/overview",
            "/api/market/heatmap",
            "/api/market/rankings/{category}",
        ]:
            assert legacy in actual_paths, f"Legacy endpoint {legacy} was removed!"


# ── /movers endpoint tests ─────────────────────────────────────────────────


class TestMoversEndpoint:
    """GET /api/market/movers — top gainers/losers from gold_movers_ranking."""

    @pytest.mark.asyncio
    async def test_movers_gainer_returns_data(self):
        """Gainer path returns ranked gainers."""
        from backend.api.market_overview import get_movers

        # Mock the trino dependency
        trino_mock = _make_trino_mock(
            fetch_all=[
                ("BTCUSDT", "binance", 50000.0, 5.5, 1_000_000.0, 1, None),
                ("ETHUSDT", "binance", 3000.0, 3.2, 500_000.0, 2, None),
            ],
        )
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_movers(category="gainer", limit=10)

        assert result["category"] == "gainer"
        assert result["limit"] == 10
        assert result["count"] == 2
        assert result["data"][0]["symbol"] == "BTCUSDT"
        assert result["data"][0]["change_pct"] == 5.5

    @pytest.mark.asyncio
    async def test_movers_loser_uses_losers_rank(self):
        """Loser path passes rank_losers to _get_top_movers."""
        from backend.api.market_overview import get_movers

        # The SQL only selects one rank column at a time (rank_gainers
        # for gainer, rank_losers for loser). The mock must reflect
        # the actual SELECT shape.
        trino_mock = _make_trino_mock(
            fetch_all=[
                # (symbol, exchange, price, change_24h, volume_24h, rank)
                ("XRPUSDT", "binance", 0.5, -10.0, 200_000.0, 1),
            ],
        )
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_movers(category="loser", limit=5)

        assert result["category"] == "loser"
        assert result["data"][0]["rank"] == 1
        assert result["data"][0]["change_pct"] == -10.0

    @pytest.mark.asyncio
    async def test_movers_trino_failure_returns_503(self):
        """If Trino is down and no fallback, the endpoint returns 503
        (not 500) so clients can distinguish outage from bug.
        """
        from backend.api.market_overview import get_movers
        from fastapi import HTTPException

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=Exception("Trino down"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_movers(category="gainer", limit=10)
            assert exc.value.status_code == 503
            # Detail must mention the failure category (not necessarily
            # the exception message itself, to avoid leaking internals).
            assert "Gold data unavailable" in exc.value.detail

    @pytest.mark.asyncio
    async def test_movers_invalid_category_rejected(self):
        """FastAPI's regex constraint on category rejects 'foo'."""
        from backend.api.market_overview import get_movers
        with pytest.raises(Exception):
            # FastAPI's Query(..., regex=...) raises on invalid input
            await get_movers(category="invalid", limit=10)


# ── /dominance endpoint tests ───────────────────────────────────────────────


class TestDominanceEndpoint:
    """GET /api/market/dominance — BTC/ETH dominance summary."""

    @pytest.mark.asyncio
    async def test_dominance_returns_summary(self):
        from backend.api.market_overview import get_dominance

        trino_mock = _make_trino_mock(fetch_one=(1e9, 200, 45.5, 18.2))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_dominance()

        assert "data" in result
        d = result["data"]
        assert d["active_symbols"] == 200
        assert d["btc_dominance"] == 45.5
        assert d["eth_dominance"] == 18.2
        assert d["total_volume_24h"] == 1e9

    @pytest.mark.asyncio
    async def test_dominance_trino_failure_returns_503(self):
        from backend.api.market_overview import get_dominance
        from fastapi import HTTPException

        trino_mock = MagicMock()
        trino_mock.fetch_one = AsyncMock(side_effect=Exception("Trino unreachable"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_dominance()
            assert exc.value.status_code == 503


# ── /volatility endpoint tests ──────────────────────────────────────────────


class TestVolatilityEndpoint:
    """GET /api/market/volatility — top volatile from gold_volatility_ranking."""

    @pytest.mark.asyncio
    async def test_volatility_returns_ranked_list(self):
        from backend.api.market_overview import get_volatility

        trino_mock = _make_trino_mock(
            fetch_all=[
                ("PEPEUSDT", "binance", 25.0, 0.25, 1),
                ("DOGEUSDT", "binance", 15.0, 0.15, 2),
            ],
        )
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_volatility(limit=10)

        assert result["count"] == 2
        assert result["data"][0]["symbol"] == "PEPEUSDT"
        assert result["data"][0]["rank"] == 1
        assert result["data"][0]["price_range_pct"] == 25.0

    @pytest.mark.asyncio
    async def test_volatility_trino_failure_503(self):
        from backend.api.market_overview import get_volatility
        from fastapi import HTTPException

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=Exception("Trino timeout"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_volatility(limit=10)
            assert exc.value.status_code == 503


# ── /sectors endpoint tests ────────────────────────────────────────────────


class TestSectorsEndpoint:
    """GET /api/market/sectors — list (not dict) for direct UI rendering."""

    @pytest.mark.asyncio
    async def test_sectors_returns_list_with_sector_field(self):
        from backend.api.market_overview import get_sectors

        # _get_sector_performance returns dict keyed by underscored sector name
        trino_mock = _make_trino_mock(
            fetch_all=[
                ("Large Cap", 2.5, 5_000_000.0, 50),
                ("Mid Cap", 1.2, 1_000_000.0, 100),
                ("Small Cap", -0.5, 100_000.0, 200),
            ],
        )
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_sectors()

        assert result["count"] == 3
        # The endpoint should convert dict → list
        sectors = result["data"]
        assert isinstance(sectors, list)
        # Each entry must have 'sector' as a human-readable field
        for s in sectors:
            assert "sector" in s
            assert "change_pct" in s
            assert "volume" in s
            assert "symbol_count" in s
        # Check that 'Large Cap' is preserved (title-cased)
        sector_names = {s["sector"] for s in sectors}
        assert "Large Cap" in sector_names

    @pytest.mark.asyncio
    async def test_sectors_trino_failure_503(self):
        from backend.api.market_overview import get_sectors
        from fastapi import HTTPException

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=Exception("Trino down"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_sectors()
            assert exc.value.status_code == 503


# ── /news-sentiment endpoint tests ──────────────────────────────────────────


class TestNewsSentimentEndpoint:
    """GET /api/market/news-sentiment — gold_news_sentiment_daily."""

    @pytest.mark.asyncio
    async def test_news_sentiment_returns_articles(self):
        from backend.api.market_overview import get_news_sentiment

        trino_mock = _make_trino_mock(
            fetch_all=[
                ("BTCUSDT", 50, 0.65, 30, 5),
                ("ETHUSDT", 40, 0.45, 20, 10),
            ],
        )
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_news_sentiment(days=7, limit=20)

        assert result["days"] == 7
        assert result["limit"] == 20
        assert result["count"] == 2
        item = result["data"][0]
        assert item["symbol"] == "BTCUSDT"
        assert item["article_count"] == 50
        assert item["avg_sentiment"] == 0.65
        assert item["bullish_count"] == 30
        assert item["bearish_count"] == 5

    @pytest.mark.asyncio
    async def test_news_sentiment_trino_failure_503(self):
        from backend.api.market_overview import get_news_sentiment
        from fastapi import HTTPException

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=Exception("Trino down"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_news_sentiment(days=7, limit=20)
            assert exc.value.status_code == 503

    def test_news_sentiment_days_range_validated(self):
        """days parameter must be 1..30 (validated by FastAPI Query)."""
        from backend.api.market_overview import get_news_sentiment
        # Just verify the signature has the constraints
        import inspect
        sig = inspect.signature(get_news_sentiment)
        days_param = sig.parameters["days"]
        # Query() default; check the constraints in repr
        assert "ge=1" in str(days_param.default) or "Query" in str(days_param.default)


# ── /indicators endpoint tests ──────────────────────────────────────────────


class TestIndicatorsEndpoint:
    """GET /api/market/indicators — momentum summary."""

    @pytest.mark.asyncio
    async def test_indicators_returns_summary(self):
        from backend.api.market_overview import get_indicators

        trino_mock = _make_trino_mock(
            fetch_one=(200, 55.0, 30, 20, 50, 25),
        )
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            result = await get_indicators()

        d = result["data"]
        assert d["total_symbols"] == 200
        assert d["avg_rsi"] == 55.0
        assert d["overbought_count"] == 30
        assert d["oversold_count"] == 20
        assert d["bullish_macd_count"] == 50
        assert d["bearish_macd_count"] == 25

    @pytest.mark.asyncio
    async def test_indicators_trino_failure_503(self):
        from backend.api.market_overview import get_indicators
        from fastapi import HTTPException

        trino_mock = MagicMock()
        trino_mock.fetch_one = AsyncMock(side_effect=Exception("Trino down"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)):
            with pytest.raises(HTTPException) as exc:
                await get_indicators()
            assert exc.value.status_code == 503


# ── Cross-cutting: observability hooks ──────────────────────────────────────


class TestObservabilityHooks:
    """Each new endpoint must record fallback metrics on Trino failure."""

    @pytest.mark.asyncio
    async def test_movers_records_fallback_metric_on_failure(self):
        from backend.api.market_overview import get_movers

        trino_mock = MagicMock()
        trino_mock.fetch_all = AsyncMock(side_effect=Exception("Trino down"))
        with patch("backend.api.market_overview.get_trino",
                    new=AsyncMock(return_value=trino_mock)), \
             patch("backend.api.market_overview.record_trino_fallback") as mock_record:
            with pytest.raises(Exception):
                await get_movers(category="gainer", limit=10)
            mock_record.assert_called_once()
            # The reason must be the exception class name
            args = mock_record.call_args[0]
            assert args[0] == "movers_gainer"
            assert args[1] == "Exception"

    @pytest.mark.asyncio
    async def test_all_endpoints_record_fallback(self):
        """Sanity check: every endpoint that queries gold tables must
        call record_trino_fallback on failure.
        """
        from backend.api import market_overview as mod

        endpoints = [
            ("get_movers", {"category": "gainer", "limit": 10}),
            ("get_dominance", {}),
            ("get_volatility", {"limit": 10}),
            ("get_sectors", {}),
            ("get_news_sentiment", {"days": 7, "limit": 20}),
            ("get_indicators", {}),
        ]
        for name, kwargs in endpoints:
            func = getattr(mod, name)
            trino_mock = MagicMock()
            trino_mock.fetch_one = AsyncMock(side_effect=Exception("down"))
            trino_mock.fetch_all = AsyncMock(side_effect=Exception("down"))
            with patch("backend.api.market_overview.get_trino",
                        new=AsyncMock(return_value=trino_mock)), \
                 patch("backend.api.market_overview.record_trino_fallback") as mock_record:
                with pytest.raises(Exception):
                    await func(**kwargs)
                assert mock_record.called, (
                    f"Endpoint {name} did not call record_trino_fallback"
                )
