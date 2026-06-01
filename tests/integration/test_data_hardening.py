"""
Integration tests for trades and orderbook metadata endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from backend.app import app


@pytest.fixture
def test_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── Trades Metadata Tests ────────────────────────────────────────────────────

class TestTradesMetadata:
    @pytest.mark.asyncio
    async def test_trades_include_metadata(self, test_client):
        """Trades response must include data_type and is_true_trade_tape metadata."""
        mock_redis = AsyncMock()
        mock_redis.zrevrange = AsyncMock(return_value=[
            ("50000:1.5", 1700000000000),
            ("49900:2.0", 1699999900000),
        ])

        with patch("backend.api.trades.get_redis", return_value=mock_redis):
            async with test_client as client:
                resp = await client.get("/api/trades/BTCUSDT")

        assert resp.status_code == 200
        data = resp.json()
        assert "metadata" in data
        assert data["metadata"]["data_type"] == "ticker_derived"
        assert data["metadata"]["is_true_trade_tape"] is False
        assert "freshness" in data["metadata"]

    @pytest.mark.asyncio
    async def test_trades_summary_endpoint(self, test_client):
        """Trade summary must include truthful data_type metadata."""
        mock_redis = AsyncMock()
        mock_redis.zrevrange = AsyncMock(return_value=[
            ("50000:1.5", 1700000000000),
            ("49900:2.0", 1699999900000),
        ])

        with patch("backend.api.trades.get_redis", return_value=mock_redis):
            async with test_client as client:
                resp = await client.get("/api/trades/BTCUSDT/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data_type"] == "ticker_derived"
        assert data["is_true_trade_tape"] is False
        assert data["tick_count"] == 2


# ── Orderbook Metadata Tests ─────────────────────────────────────────────────

class TestOrderbookMetadata:
    @pytest.mark.asyncio
    async def test_orderbook_includes_metadata(self, test_client):
        """Orderbook response must include source and freshness metadata."""
        mock_redis = AsyncMock()
        import json
        import time
        event_time = int(time.time() * 1000)
        mock_redis.hgetall = AsyncMock(return_value={
            "bids": json.dumps([[50000, 1.5]]),
            "asks": json.dumps([[50100, 2.0]]),
            "spread": "100",
            "best_bid": "50000",
            "best_ask": "50100",
            "event_time": str(event_time),
        })

        with patch("backend.api.orderbook.get_redis", return_value=mock_redis):
            async with test_client as client:
                resp = await client.get("/api/orderbook/BTCUSDT")

        assert resp.status_code == 200
        data = resp.json()
        assert "metadata" in data
        assert data["metadata"]["source"] == "redis"
        assert data["metadata"]["is_synthetic"] is False
        assert "freshness" in data["metadata"]

    @pytest.mark.asyncio
    async def test_orderbook_summary_endpoint(self, test_client):
        """Orderbook summary must include depth and imbalance."""
        mock_redis = AsyncMock()
        import json
        import time
        event_time = int(time.time() * 1000)
        mock_redis.hgetall = AsyncMock(return_value={
            "bids": json.dumps([[50000, 1.5], [49900, 2.0]]),
            "asks": json.dumps([[50100, 1.0], [50200, 0.5]]),
            "spread": "100",
            "best_bid": "50000",
            "best_ask": "50100",
            "event_time": str(event_time),
        })

        with patch("backend.api.orderbook.get_redis", return_value=mock_redis):
            async with test_client as client:
                resp = await client.get("/api/orderbook/BTCUSDT/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert "bid_depth" in data
        assert "ask_depth" in data
        assert "imbalance" in data
        assert "spread" in data


# ── Market Overview Metadata Tests ────────────────────────────────────────────

class TestMarketOverviewMetadata:
    @pytest.mark.asyncio
    async def test_overview_includes_placeholder_metadata(self, test_client):
        """Market overview must indicate when data is placeholder."""
        with patch("backend.api.market_overview.get_trino") as mock_trino:
            mock_trino.return_value = AsyncMock()
            async with test_client as client:
                resp = await client.get("/api/market/overview")

        assert resp.status_code == 200
        data = resp.json()
        assert "metadata" in data
        assert data["metadata"]["is_placeholder"] is True
