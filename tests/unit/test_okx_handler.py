"""
Unit tests for OKX message handling in producer main.py.

Tests the _handle_okx_message function which parses OKX WebSocket
subscription frame responses and dispatches to the correct Kafka topic.

Note: _handle_okx_message takes 3 args (message, client, tag) - it uses
avro_serializer from global scope in producer/main.py
"""

import sys
import os
import json
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from unittest.mock import MagicMock, patch


# ── Test fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_client():
    """Create a mock OKX client with mappers."""
    client = MagicMock()
    client.map_ticker = MagicMock(return_value={
        "event_time": 1609459200000,
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "close": 50000.0,
    })
    client.map_trade = MagicMock(return_value={
        "event_time": 1609459200000,
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "price": 50000.0,
    })
    client.map_kline = MagicMock(return_value={
        "event_time": 1609459200000,
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "open": 50000.0,
        "high": 50500.0,
        "low": 49500.0,
        "close": 50200.0,
    })
    client.map_depth = MagicMock(return_value={
        "event_time": 1609459200000,
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "bids": "[]",
        "asks": "[]",
    })
    return client


# ── Test imports ───────────────────────────────────────────────────────────────

def get_handler_module():
    """Import handler function from main module."""
    from producer.main import _handle_okx_message
    return _handle_okx_message


class TestHandleOKXMessage:
    """Test OKX message handler."""

    def test_subscribe_confirmation_skipped(self, mock_client):
        """Subscribe confirmations are silently skipped."""
        handler = get_handler_module()

        # Subscribe confirmation
        msg = json.dumps({"event": "subscribe", "arg": {"channel": "tickers"}})

        with patch("producer.main.send_to_kafka") as mock_send:
            handler(msg, mock_client, "TICKER")
            mock_send.assert_not_called()

    def test_unsubscribe_confirmation_skipped(self, mock_client):
        """Unsubscribe confirmations are silently skipped."""
        handler = get_handler_module()

        msg = json.dumps({"event": "unsubscribe", "arg": {"channel": "tickers"}})

        with patch("producer.main.send_to_kafka") as mock_send:
            handler(msg, mock_client, "TICKER")
            mock_send.assert_not_called()

    def test_error_event_logged(self, mock_client):
        """Error events are logged but don't crash."""
        handler = get_handler_module()

        msg = json.dumps({
            "event": "error",
            "code": "60000",
            "msg": "Invalid channel",
            "arg": {"channel": "invalid"}
        })

        # Should not raise
        with patch("producer.main.send_to_kafka") as mock_send:
            with patch("producer.main.log") as mock_log:
                handler(msg, mock_client, "TICKER")
                mock_log.error.assert_called_once()
                mock_send.assert_not_called()

    def test_ticker_channel_dispatched(self, mock_client):
        """Tickers are mapped and sent to ticker topic."""
        handler = get_handler_module()

        msg = json.dumps({
            "arg": {"channel": "tickers", "instId": "BTC-USDT"},
            "data": [{
                "instId": "BTC-USDT",
                "last": "50000",
                "ts": "1609459200000"
            }]
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            with patch("producer.main.KAFKA_TOPIC_TICKER", "crypto_ticker"):
                handler(msg, mock_client, "TICKER")
                mock_send.assert_called_once()
                args = mock_send.call_args
                assert args[0][0] == "crypto_ticker"

    def test_trades_channel_dispatched(self, mock_client):
        """Trades are mapped and sent to trades topic."""
        handler = get_handler_module()

        msg = json.dumps({
            "arg": {"channel": "trades", "instId": "BTC-USDT"},
            "data": [{
                "instId": "BTC-USDT",
                "tradeId": "12345",
                "px": "50000",
                "sz": "1.5",
                "side": "buy",
                "ts": "1609459200000"
            }]
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            with patch("producer.main.KAFKA_TOPIC_TRADES", "crypto_trades"):
                handler(msg, mock_client, "TRADES")
                mock_send.assert_called_once()
                args = mock_send.call_args
                assert args[0][0] == "crypto_trades"

    def test_kline_channel_dispatched(self, mock_client):
        """Klines are mapped and sent to klines topic."""
        handler = get_handler_module()

        # OKX kline data as array
        msg = json.dumps({
            "arg": {"channel": "candle1m", "instId": "BTC-USDT"},
            "data": [[
                "1609459200000",  # ts
                "50000",          # o
                "50500",          # h
                "49500",          # l
                "50200",          # c
                "100",            # vol
                "5000000",        # volCcy
                "1"               # confirm
            ]]
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            with patch("producer.main.KAFKA_TOPIC_KLINES", "crypto_klines"):
                handler(msg, mock_client, "KLINES")
                mock_send.assert_called_once()
                args = mock_send.call_args
                assert args[0][0] == "crypto_klines"
                # Symbol should be set on mapped kline
                mapped = args[0][1]
                assert mapped["symbol"] == "BTCUSDT"

    def test_depth_channel_dispatched(self, mock_client):
        """Depth/orderbook is mapped and sent to depth topic."""
        handler = get_handler_module()

        msg = json.dumps({
            "arg": {"channel": "books5", "instId": "BTC-USDT"},
            "data": [{
                "asks": [["50001", "1.5"]],
                "bids": [["49999", "2.0"]],
                "ts": "1609459200000",
                "checksum": 123456
            }]
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            with patch("producer.main.KAFKA_TOPIC_DEPTH", "crypto_depth"):
                handler(msg, mock_client, "DEPTH")
                mock_send.assert_called_once()
                args = mock_send.call_args
                assert args[0][0] == "crypto_depth"
                mapped = args[0][1]
                assert mapped["symbol"] == "BTCUSDT"

    def test_non_usdt_symbol_skipped(self, mock_client):
        """Non-USDT symbols are filtered out."""
        handler = get_handler_module()

        msg = json.dumps({
            "arg": {"channel": "tickers", "instId": "BTC-BTC"},  # Not USDT
            "data": [{"instId": "BTC-BTC", "last": "50000"}]
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            handler(msg, mock_client, "TICKER")
            mock_send.assert_not_called()

    def test_empty_data_skipped(self, mock_client):
        """Empty data arrays are skipped."""
        handler = get_handler_module()

        msg = json.dumps({
            "arg": {"channel": "tickers", "instId": "BTC-USDT"},
            "data": []
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            handler(msg, mock_client, "TICKER")
            mock_send.assert_not_called()

    def test_invalid_json_skipped(self, mock_client):
        """Invalid JSON is gracefully skipped."""
        handler = get_handler_module()

        msg = "not valid json {{{"

        with patch("producer.main.send_to_kafka") as mock_send:
            handler(msg, mock_client, "TICKER")
            mock_send.assert_not_called()

    def test_multiple_data_items_processed(self, mock_client):
        """Multiple data items in array are all processed."""
        handler = get_handler_module()

        msg = json.dumps({
            "arg": {"channel": "tickers", "instId": "BTC-USDT"},
            "data": [
                {"instId": "BTC-USDT", "last": "50000", "ts": "1609459200000"},
                {"instId": "BTC-USDT", "last": "50001", "ts": "1609459201000"},
                {"instId": "BTC-USDT", "last": "50002", "ts": "1609459202000"},
            ]
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            with patch("producer.main.KAFKA_TOPIC_TICKER", "crypto_ticker"):
                handler(msg, mock_client, "TICKER")
                assert mock_send.call_count == 3


class TestSymbolNormalization:
    """Test symbol normalization in OKX handler."""

    def test_symbol_uppercase_and_no_dash(self, mock_client):
        """Symbol is converted from BTC-USDT to BTCUSDT."""
        handler = get_handler_module()

        msg = json.dumps({
            "arg": {"channel": "trades", "instId": "eth-usdt"},
            "data": [{
                "instId": "eth-usdt",
                "tradeId": "123",
                "px": "3000",
                "sz": "1.0",
                "side": "buy",
                "ts": "1609459200000"
            }]
        })

        with patch("producer.main.send_to_kafka") as mock_send:
            handler(msg, mock_client, "TRADES")
            # The symbol should be uppercased and dash removed
            mock_client.map_trade.assert_called()
            call_arg = mock_client.map_trade.call_args[0][0]
            assert call_arg["instId"] == "eth-usdt"