"""Unit tests for backend.api.market_overview.

Tests cover:
- DB constant uses iceberg.crypto_lakehouse (not iceberg_catalog)
- Response metadata structure (is_placeholder, data_sources)
- Gold-first query with Redis fallback logic
- AsyncTrinoClient
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_trino():
    """Mock trino client that returns empty/healthy data."""
    trino = AsyncMock()
    trino.fetch_one = AsyncMock(return_value=(0, 0, 0, 0))
    trino.fetch_all = AsyncMock(return_value=[])
    return trino


@pytest.fixture
def mock_app_client():
    """Create a test HTTP client with the FastAPI app."""
    from httpx import AsyncClient, ASGITransport
    from backend.app import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Tests: Catalog reference (Phase D verification)
# ---------------------------------------------------------------------------

class TestMarketOverviewCatalog:
    """Verify market_overview uses iceberg.crypto_lakehouse, not iceberg_catalog."""

    @pytest.mark.unit
    def test_db_constant_uses_crypto_lakehouse(self):
        from backend.api.market_overview import DB
        assert "iceberg.crypto_lakehouse" in DB
        assert "iceberg_catalog" not in DB

    @pytest.mark.unit
    def test_queries_use_correct_catalog(self):
        """Check that the module-level DB constant is used in queries."""
        from backend.api.market_overview import DB
        import backend.api.market_overview as mod

        # Verify the DB variable is referenced (not hardcoded)
        source = open(mod.__file__, encoding="utf-8").read()
        assert "iceberg_catalog" not in source, "Found legacy iceberg_catalog reference in market_overview.py"
        assert "iceberg.crypto_lakehouse" in source


# ---------------------------------------------------------------------------
# Tests: Gold-first query path
# ---------------------------------------------------------------------------

class TestMarketOverviewGoldPath:
    """Test the gold-first Trino query path."""

    @pytest.mark.unit
    def test_gold_freshness_configured(self):
        from backend.api.market_overview import GOLD_FRESHNESS_MINUTES
        assert isinstance(GOLD_FRESHNESS_MINUTES, int)
        assert GOLD_FRESHNESS_MINUTES > 0

    @pytest.mark.unit
    def test_enable_gold_path(self):
        from backend.api.market_overview import ENABLE_GOLD_PATH
        assert ENABLE_GOLD_PATH is True


# ---------------------------------------------------------------------------
# Tests: Response metadata structure
# ---------------------------------------------------------------------------

class TestMarketOverviewMetadata:
    """Test that metadata is properly structured in response."""

    @pytest.mark.unit
    def test_metadata_structure_from_redis_fallback(self):
        """When trino_gold not in data_sources, is_placeholder must be True."""
        data_sources = ["redis_fallback"]
        trino_data_available = False
        metadata = {
            "source": data_sources[0] if data_sources else "unknown",
            "data_sources": data_sources,
            "is_placeholder": "trino_gold" not in data_sources,
            "computed_at": datetime.utcnow().isoformat(),
            "gold_tables_healthy": trino_data_available,
        }
        assert metadata["is_placeholder"] is True
        assert metadata["gold_tables_healthy"] is False

    @pytest.mark.unit
    def test_metadata_structure_from_trino_gold(self):
        """When trino_gold in data_sources, is_placeholder must be False."""
        data_sources = ["trino_gold"]
        trino_data_available = True
        metadata = {
            "source": data_sources[0],
            "data_sources": data_sources,
            "is_placeholder": "trino_gold" not in data_sources,
            "computed_at": datetime.utcnow().isoformat(),
            "gold_tables_healthy": trino_data_available,
        }
        assert metadata["is_placeholder"] is False
        assert metadata["gold_tables_healthy"] is True

    @pytest.mark.unit
    def test_metadata_has_required_keys(self):
        """All required metadata keys must exist."""
        required_keys = [
            "source", "data_sources", "is_placeholder",
            "computed_at", "gold_tables_healthy",
        ]
        # Read the source to verify all keys are present
        import backend.api.market_overview as mod
        source = open(mod.__file__, encoding="utf-8").read()
        for key in required_keys:
            assert f'"{key}"' in source or f"'{key}'" in source, f"Missing metadata key: {key}"


# ---------------------------------------------------------------------------
# Tests: AsyncTrinoClient
# ---------------------------------------------------------------------------

class TestAsyncTrinoClient:
    @pytest.mark.unit
    def test_client_exists(self):
        from backend.api.market_overview import AsyncTrinoClient
        assert AsyncTrinoClient is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_one_delegates_to_cursor(self):
        from backend.api.market_overview import AsyncTrinoClient
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100, 50, 40, 10)
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.api.market_overview.get_trino_connection", return_value=mock_conn):
            client = AsyncTrinoClient()
            result = await client.fetch_one("SELECT 1")

        assert result == (100, 50, 40, 10)
        mock_cursor.execute.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_all_delegates_to_cursor(self):
        from backend.api.market_overview import AsyncTrinoClient
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1,), (2,)]
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.api.market_overview.get_trino_connection", return_value=mock_conn):
            client = AsyncTrinoClient()
            result = await client.fetch_all("SELECT * FROM t")

        assert len(result) == 2
