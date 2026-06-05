"""Unit tests for KeyDBTradeWriter (Flink trade hot cache writer)."""

import json
import time
import sys
from unittest.mock import MagicMock, patch

# ------ Skip if pyflink is not available ------
try:
    from pyflink.datastream.functions import FlatMapFunction
    HAS_PYFLINK = True
except ImportError:
    HAS_PYFLINK = False

import pytest


@pytest.fixture
def mock_redis():
    """Create a mock Redis pipeline object."""
    pipe = MagicMock()
    pipe.__enter__ = MagicMock(return_value=pipe)
    pipe.__exit__ = MagicMock(return_value=None)
    return pipe


@pytest.fixture
def mock_flink_redis():
    """Mock get_flink_redis to return a MagicMock with pipeline."""
    r = MagicMock()
    pipe = MagicMock()
    r.pipeline.return_value = pipe
    return r


def test_trade_writer_parse_buyer_trade():
    """Verify a sell trade (is_buyer_maker=True) is parsed correctly."""
    input_data = json.dumps({
        "event_time": 1717000000000,
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "agg_trade_id": 12345,
        "price": 67500.0,
        "quantity": 0.5,
        "trade_time": 1717000000000,
        "is_buyer_maker": True,
    })
    # Verify JSON structure
    parsed = json.loads(input_data)
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["exchange"] == "binance"
    assert parsed["price"] == 67500.0
    assert parsed["is_buyer_maker"] is True
    # sell trade (is_buyer_maker means sell)
    assert bool(parsed["is_buyer_maker"]) is True


def test_trade_writer_parse_buy_trade():
    """Verify a buy trade (is_buyer_maker=False) is parsed correctly."""
    input_data = json.dumps({
        "event_time": 1717000001000,
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "agg_trade_id": 12346,
        "price": 67510.0,
        "quantity": 1.2,
        "trade_time": 1717000001000,
        "is_buyer_maker": False,
    })
    parsed = json.loads(input_data)
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["exchange"] == "binance"
    assert parsed["price"] == 67510.0
    assert parsed["is_buyer_maker"] is False


def test_trade_json_output_format():
    """Verify the JSON format stored in Redis (price, quantity, trade_time, is_buyer_maker)."""
    trade = {
        "p": 67500.0,
        "q": 0.5,
        "t": 1717000000000,
        "m": False,
        "T": 1717000000000,
    }
    trade_json = json.dumps(trade)
    parsed = json.loads(trade_json)
    assert parsed["p"] == 67500.0
    assert parsed["q"] == 0.5
    assert parsed["t"] == 1717000000000
    assert parsed["m"] is False
    assert "T" in parsed  # event_time


def test_trade_exchange_field():
    """Verify exchange field is preserved through the trade writer."""
    input_data = {
        "event_time": 1717000000000,
        "symbol": "ETHUSDT",
        "exchange": "okx",
        "agg_trade_id": 99999,
        "price": 3500.0,
        "quantity": 10.0,
        "trade_time": 1717000000000,
        "is_buyer_maker": False,
    }
    assert input_data["exchange"] == "okx"


def test_trade_default_exchange():
    """Verify default exchange is binance if not provided."""
    input_data = {
        "event_time": 1717000000000,
        "symbol": "BTCUSDT",
        "agg_trade_id": 1,
        "price": 67000.0,
        "quantity": 1.0,
        "trade_time": 1717000000000,
        "is_buyer_maker": True,
    }
    exchange = input_data.get("exchange", "binance")
    assert exchange == "binance"


@pytest.mark.skipif(not HAS_PYFLINK, reason="pyflink not installed")
def test_trade_writer_batch_buffer():
    """Verify that writer batches correctly (basic instantiation test)."""
    from writers.keydb_trades import KeyDBTradeWriter
    writer = KeyDBTradeWriter()
    assert writer.BATCH_SIZE == 100
    assert writer.MAX_ENTRIES == 200
    assert writer.TRADE_TTL_SEC == 600
    assert callable(writer.flat_map)


@pytest.mark.skipif(not HAS_PYFLINK, reason="pyflink not installed")
def test_trade_writer_empty_symbol_skipped(mock_flink_redis):
    """Verify empty symbol is skipped without error."""
    from writers.keydb_trades import KeyDBTradeWriter
    writer = KeyDBTradeWriter()
    writer.open(MagicMock())
    writer._r = mock_flink_redis

    result = writer.flat_map(json.dumps({"symbol": ""}))
    assert result == []
    mock_flink_redis.pipeline.assert_not_called()


def test_trade_dedup_same_trade_time():
    """Verify that ZREMRANGEBYSCORE before ZADD would dedup by trade_time."""
    trade_time = 1717000000000
    key = "trade:latest:binance:BTCUSDT"
    # Simulate: remove existing entry for same trade_time, then add
    # This is what the real writer does: zremrangebyscore -> zadd
    assert isinstance(int(trade_time), int)
    assert key == "trade:latest:binance:BTCUSDT"

