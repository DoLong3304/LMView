import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from backend.app import app


class MockTrinoClient:
    def __init__(self, one_return=None, all_return=None):
        self.one_return = one_return or (0,) * 10
        self.all_return = all_return or []
        self.fetch_one = AsyncMock(return_value=self.one_return)
        self.fetch_all = AsyncMock(return_value=self.all_return)


@pytest.mark.integration
class TestMarketOverviewEndpoint:

    @pytest.mark.asyncio
    async def test_get_overview(self):
        """Test the market overview endpoint with mocked Trino data."""
        mock_trino = MockTrinoClient(
            one_return=(1000000.0, 500000.0, 50.0, 20.0, 100, 50)
        )
        with patch("backend.api.market_overview.get_trino", return_value=mock_trino):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/market/overview")
                
            assert resp.status_code == 200
            data = resp.json()
            assert "market_summary" in data
            assert data["market_summary"]["total_market_cap"] == 0
            assert data["market_summary"]["btc_dominance"] == 0

    @pytest.mark.asyncio
    async def test_get_heatmap(self):
        """Test the heatmap endpoint with mocked Trino data."""
        mock_trino = MockTrinoClient(
            all_return=[("BTCUSDT", 2.5, 50000.0, 1000.0, 500000000.0, 0.05)]
        )
        with patch("backend.api.market_overview.get_trino", return_value=mock_trino):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/market/heatmap")
                
            assert resp.status_code == 200
            data = resp.json()
            assert "data" in data
            assert len(data["data"]) == 1
            assert data["data"][0]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_rankings_gainers(self):
        """Test the rankings endpoint for gainers."""
        mock_trino = MockTrinoClient(
            all_return=[("ETHUSDT", 1, 10.5, 3000.0, 500.0, 5.0)]
        )
        with patch("backend.api.market_overview.get_trino", return_value=mock_trino):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/market/rankings/gainers")
                
            assert resp.status_code == 200
            data = resp.json()
            assert data["category"] == "gainers"
            assert len(data["data"]) == 1
            assert data["data"][0]["symbol"] == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_get_rankings_invalid_category(self):
        """Test that invalid categories return a 400 Bad Request."""
        mock_trino = MockTrinoClient()
        with patch("backend.api.market_overview.get_trino", return_value=mock_trino):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/market/rankings/invalid_cat")
                
            assert resp.status_code == 400
