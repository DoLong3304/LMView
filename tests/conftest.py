"""
Shared test fixtures and configuration.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set environment variables before any backend imports
os.environ.setdefault("INFLUX_TOKEN", "test-token")
os.environ.setdefault("INFLUX_URL", "http://localhost:8086")
os.environ.setdefault("INFLUX_ORG", "test-org")
os.environ.setdefault("INFLUX_BUCKET", "test-bucket")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("TRINO_HOST", "localhost")
os.environ.setdefault("TRINO_PORT", "8080")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_LMVIEW_DB", "test_lmview")


@pytest.fixture
def sample_candles():
    """Sample OHLCV candle data for testing."""
    return [
        {"openTime": 1000000, "open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0, "volume": 50.0},
        {"openTime": 1060000, "open": 105.0, "high": 115.0, "low": 100.0, "close": 110.0, "volume": 60.0},
        {"openTime": 1120000, "open": 110.0, "high": 120.0, "low": 105.0, "close": 115.0, "volume": 70.0},
        {"openTime": 1180000, "open": 115.0, "high": 125.0, "low": 110.0, "close": 120.0, "volume": 80.0},
        {"openTime": 1240000, "open": 120.0, "high": 130.0, "low": 115.0, "close": 125.0, "volume": 90.0},
    ]


@pytest.fixture
def sample_1m_candles():
    """10 one-minute candles with 60s spacing for aggregation tests."""
    base_time = 1700000000000  # ~Nov 2023
    candles = []
    for i in range(10):
        t = base_time + i * 60000
        price = 100.0 + i
        candles.append({
            "openTime": t,
            "open": price,
            "high": price + 5.0,
            "low": price - 2.0,
            "close": price + 3.0,
            "volume": 10.0 + i,
        })
    return candles


@pytest.fixture(autouse=True)
def mock_background_tasks():
    """Mock background fetchers and PostgreSQL to prevent them from starting during tests."""
    patches = []
    try:
        patches.append(patch("backend.app.news_fetcher.start"))
        patches.append(patch("backend.app.news_fetcher.stop"))
        patches.append(patch("backend.app.market_fetcher.start"))
        patches.append(patch("backend.app.market_fetcher.stop"))
        patches.append(patch("backend.app.init_pg_pool"))
        patches.append(patch("backend.app.close_pg_pool"))
        patches.append(patch("backend.app.run_migration"))

        for p in patches:
            p.start()
    except (ImportError, AttributeError, ModuleNotFoundError):
        # Some modules may not be importable in local dev (missing influxdb_client, etc.)
        # Unit tests for models/security don't need the full app
        pass

    yield

    for p in patches:
        try:
            p.stop()
        except (RuntimeError, AttributeError):
            pass
