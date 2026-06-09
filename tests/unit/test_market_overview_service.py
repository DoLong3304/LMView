"""Unit tests for backend.services.market_overview_service.

Tests cover:
- MarketOverviewService initialization
- get_metrics returns correct structure
- get_top_gainers sorts by change correctly
- get_top_losers sorts by change correctly
- get_sector_performance groups coins by sector
- Cache TTL is set correctly
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import importlib


class TestMarketOverviewService:
    """Test MarketOverviewService methods."""

    @pytest.fixture
    def mock_redis_with_tickers(self):
        """Mock Redis client with ticker data."""
        redis = AsyncMock()
        redis.scan = AsyncMock(return_value=(0, [
            "ticker:latest:binance:BTCUSDT",
            "ticker:latest:binance:ETHUSDT",
            "ticker:latest:binance:SOLUSDT",
        ]))
        redis.hgetall = AsyncMock(side_effect=[
            {"price": "50000", "change24h": "2.5", "volume": "1000000"},
            {"price": "3000", "change24h": "3.0", "volume": "500000"},
            {"price": "100", "change24h": "10.0", "volume": "200000"},
        ])
        return redis

    @pytest.fixture
    def empty_redis(self):
        """Mock Redis with no tickers."""
        redis = AsyncMock()
        redis.scan = AsyncMock(return_value=(0, []))
        redis.hgetall = AsyncMock(return_value={})
        return redis

    @pytest.mark.asyncio
    async def test_service_initialization(self, empty_redis):
        """Service initializes with correct cache TTL."""
        with patch("backend.core.database.get_redis", return_value=empty_redis):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            assert service._cache_ttl == 60

    @pytest.mark.asyncio
    async def test_get_metrics_returns_structure(self, mock_redis_with_tickers):
        """get_metrics returns correct market metrics structure."""
        with patch("backend.core.database.get_redis", return_value=mock_redis_with_tickers):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            result = await service.get_metrics()

            assert "total_market_cap" in result
            assert "total_volume_24h" in result
            assert "btc_dominance" in result
            assert "eth_dominance" in result
            assert "fear_greed_index" in result
            assert "btc_price" in result
            assert "advancing_count" in result
            assert "declining_count" in result

    @pytest.mark.asyncio
    async def test_cache_ttl_is_60_seconds(self, empty_redis):
        """Cache TTL is set to 60 seconds."""
        with patch("backend.core.database.get_redis", return_value=empty_redis):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            assert service._cache_ttl == 60

    @pytest.mark.asyncio
    async def test_empty_metrics_structure(self, empty_redis):
        """_empty_metrics returns correct structure with zeros."""
        with patch("backend.core.database.get_redis", return_value=empty_redis):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            metrics = service._empty_metrics()

            assert metrics["total_market_cap"] == 0
            assert metrics["total_volume_24h"] == 0
            assert metrics["btc_dominance"] == 0
            assert metrics["eth_dominance"] == 0
            assert metrics["fear_greed_index"] == 50
            assert metrics["active_symbols"] == 0

    @pytest.mark.asyncio
    async def test_get_top_gainers_sorts_correctly(self, mock_redis_with_tickers):
        """get_top_gainers returns symbols sorted by 24h change descending."""
        with patch("backend.core.database.get_redis", return_value=mock_redis_with_tickers):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            gainers = await service.get_top_gainers("day", 10)

            assert len(gainers) == 3
            # SOL has highest change (10%), should be first
            assert gainers[0]["symbol"] == "SOLUSDT"
            assert gainers[0]["change_24h_pct"] == 10.0
            # BTC has lowest change (2.5%), should be last
            assert gainers[-1]["symbol"] == "BTCUSDT"
            assert gainers[-1]["change_24h_pct"] == 2.5

    @pytest.mark.asyncio
    async def test_get_top_losers_sorts_correctly(self, mock_redis_with_tickers):
        """get_top_losers returns symbols sorted by 24h change ascending."""
        with patch("backend.core.database.get_redis", return_value=mock_redis_with_tickers):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            losers = await service.get_top_losers("day", 10)

            assert len(losers) == 3
            # BTC has lowest change (2.5%), should be first for losers
            assert losers[0]["symbol"] == "BTCUSDT"
            assert losers[0]["change_24h_pct"] == 2.5

    @pytest.mark.asyncio
    async def test_get_sector_performance_returns_list(self, mock_redis_with_tickers):
        """get_sector_performance returns list of sector performance."""
        with patch("backend.core.database.get_redis", return_value=mock_redis_with_tickers):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            result = await service.get_sector_performance()

            assert isinstance(result, list)
            # Should have sectors
            sector_ids = [s["sector"] for s in result]
            assert "layer1" in sector_ids

    @pytest.mark.asyncio
    async def test_get_metrics_with_no_tickers(self, empty_redis):
        """get_metrics returns empty structure when no tickers."""
        with patch("backend.core.database.get_redis", return_value=empty_redis):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            metrics = await service.get_metrics()

            assert metrics["total_market_cap"] == 0
            assert metrics["active_symbols"] == 0
            assert metrics["advancing_count"] == 0
            assert metrics["declining_count"] == 0

    @pytest.mark.asyncio
    async def test_get_top_gainers_with_no_tickers(self, empty_redis):
        """get_top_gainers returns empty list when no tickers."""
        with patch("backend.core.database.get_redis", return_value=empty_redis):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            gainers = await service.get_top_gainers("day", 10)

            assert gainers == []

    @pytest.mark.asyncio
    async def test_get_top_losers_with_no_tickers(self, empty_redis):
        """get_top_losers returns empty list when no tickers."""
        with patch("backend.core.database.get_redis", return_value=empty_redis):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            losers = await service.get_top_losers("day", 10)

            assert losers == []

    @pytest.mark.asyncio
    async def test_get_overview_returns_complete_structure(self, mock_redis_with_tickers):
        """get_overview returns complete market overview."""
        # Create a fresh mock with enough side_effects for multiple _get_tickers calls
        redis = AsyncMock()
        redis.scan = AsyncMock(return_value=(0, [
            "ticker:latest:binance:BTCUSDT",
            "ticker:latest:binance:ETHUSDT",
        ]))
        redis.hgetall = AsyncMock(side_effect=[
            # First _get_tickers call
            {"price": "50000", "change24h": "2.5", "volume": "1000000"},
            {"price": "3000", "change24h": "3.0", "volume": "500000"},
            # Second _get_tickers call (top_gainers)
            {"price": "50000", "change24h": "2.5", "volume": "1000000"},
            {"price": "3000", "change24h": "3.0", "volume": "500000"},
            # Third _get_tickers call (top_losers)
            {"price": "50000", "change24h": "2.5", "volume": "1000000"},
            {"price": "3000", "change24h": "3.0", "volume": "500000"},
            # Fourth _get_tickers call (most_volatile)
            {"price": "50000", "change24h": "2.5", "volume": "1000000"},
            {"price": "3000", "change24h": "3.0", "volume": "500000"},
            # Fifth _get_tickers call (highest_volume)
            {"price": "50000", "change24h": "2.5", "volume": "1000000"},
            {"price": "3000", "change24h": "3.0", "volume": "500000"},
            # Sixth _get_tickers call (sector_performance)
            {"price": "50000", "change24h": "2.5", "volume": "1000000"},
            {"price": "3000", "change24h": "3.0", "volume": "500000"},
        ])

        with patch("backend.core.database.get_redis", return_value=redis):
            import backend.services.market_overview_service as module
            importlib.reload(module)
            from backend.services.market_overview_service import MarketOverviewService
            service = MarketOverviewService()
            overview = await service.get_overview()

            assert "timestamp" in overview
            assert "timeframe" in overview
            assert "market_summary" in overview
            assert "top_gainers" in overview
            assert "top_losers" in overview
            assert "metadata" in overview
            assert overview["metadata"]["source"] == "service"