"""
Pytest fixtures for Chapter 4 performance/evaluation tests.
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_ticker_message() -> dict:
    """Simulate a Binance ticker message as received by producer."""
    now_ms = int(time.time() * 1000)
    return {
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "price": 50000.0,
        "volume": 100.0,
        "event_time": now_ms - 50,
        "producer_ts": now_ms - 2,
        "redis_ts": now_ms,
    }


@pytest.fixture
def mock_redis_cache():
    """Mock Redis client for cache operations."""
    fake_store: dict = {}

    def mock_hget(key, field):
        val = fake_store.get(f"{key}:{field}")
        return val

    def mock_hset(key, field, value):
        fake_store[f"{key}:{field}"] = value
        return 1

    def mock_get(key):
        return fake_store.get(key)

    def mock_set(key, val):
        fake_store[key] = val

    mock = MagicMock()
    mock.hget.side_effect = mock_hget
    mock.hset.side_effect = mock_hset
    mock.get.side_effect = mock_get
    mock.set.side_effect = mock_set
    return mock


@pytest.fixture
def mock_influx_client():
    """Mock InfluxDB client for latency measurements."""
    mock = MagicMock()
    mock.query_api.return_value.query.return_value = []
    return mock


@pytest.fixture
def mock_trino_client():
    """Mock Trino DB API cursor."""
    mock = MagicMock()
    mock.fetchall.return_value = []
    return mock


@pytest.fixture
def mock_fastapi_app():
    """Create a minimal FastAPI test app with mocked dependencies."""
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/api/ticker/{symbol}")
        async def get_ticker(symbol: str):
            return {"symbol": symbol, "price": 50000.0, "change": 1.2}

        @app.get("/api/klines")
        async def get_klines(symbol: str = "BTCUSDT", interval: str = "1m",
                             limit: int = 100):
            import time
            base = int(time.time() * 1000)
            return [
                {"openTime": base - (limit - i) * 60000,
                 "open": 50000.0, "high": 50100.0, "low": 49900.0,
                 "close": 50050.0, "volume": 100.0}
                for i in range(limit)
            ]

        @app.get("/api/orderbook/{symbol}")
        async def get_orderbook(symbol: str):
            return {"symbol": symbol, "bids": [[50000.0, 1.0]], "asks": [[50001.0, 1.0]]}

        @app.get("/api/trades/{symbol}")
        async def get_trades(symbol: str):
            return [{"price": 50000.0, "volume": 1.0, "time": int(time.time() * 1000)}]

        @app.get("/api/market/overview")
        async def market_overview():
            return {"total_symbols": 671, "btc_dominance": 42.5}

        return TestClient(app)
    except ImportError:
        pytest.skip("FastAPI not installed")


@pytest.fixture
def client_with_mocks(mock_fastapi_app):
    """Provide a FastAPI TestClient for in-process latency measurement."""
    return mock_fastapi_app
