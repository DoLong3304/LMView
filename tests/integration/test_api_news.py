import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from backend.app import app


@pytest.mark.integration
class TestNewsEndpoint:

    @pytest.mark.asyncio
    async def test_get_latest_news(self):
        """Test getting the latest news."""
        mock_data = [{"title": "Bitcoin surges", "source": "CryptoNews", "symbol": "BTC"}]
        with patch("backend.api.news.news_service.get_latest", return_value=mock_data):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/news/latest?limit=10")
                
            assert resp.status_code == 200
            assert resp.json() == mock_data

    @pytest.mark.asyncio
    async def test_get_news_sources(self):
        """Test getting news sources."""
        mock_data = ["CryptoNews", "CoinDesk"]
        with patch("backend.api.news.news_service.get_sources", return_value=mock_data):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/news/sources")
                
            assert resp.status_code == 200
            assert resp.json() == mock_data

    @pytest.mark.asyncio
    async def test_get_trending_news(self):
        """Test getting trending news."""
        mock_data = [{"title": "Market up", "sentiment": "positive"}]
        with patch("backend.api.news.news_service.get_trending", return_value=mock_data):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/news/trending")
                
            assert resp.status_code == 200
            assert resp.json() == mock_data

    @pytest.mark.asyncio
    async def test_get_symbol_sentiment(self):
        """Test getting sentiment for a symbol."""
        mock_data = {"symbol": "BTC", "sentiment": 0.8}
        with patch("backend.api.news.news_service.get_symbol_sentiment", return_value=mock_data):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/news/sentiment/BTC")
                
            assert resp.status_code == 200
            assert resp.json() == mock_data

    @pytest.mark.asyncio
    async def test_search_news(self):
        """Test searching news."""
        mock_data = [{"title": "Ethereum upgrade", "source": "CoinTelegraph"}]
        with patch("backend.api.news.news_service.search_news", return_value=mock_data):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/news/search?q=Ethereum")
                
            assert resp.status_code == 200
            assert resp.json() == mock_data

    @pytest.mark.asyncio
    async def test_search_news_missing_query(self):
        """Test search validation for missing query parameter."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/news/search")
            
        assert resp.status_code == 422
