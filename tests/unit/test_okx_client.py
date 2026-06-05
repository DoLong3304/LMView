"""
Unit tests for OKX exchange client and mappers.

Tests cover:
- OKXClient symbol fetching and REST API
- OKX mappers (ticker, trade, kline, depth)
- Subscription frame building
- normalize_symbol utility
"""

import sys
import os

# Add src to path for direct exchange imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import json
import time
import pytest

from exchanges.okx.client import OKXClient
from exchanges.okx import mappers


class TestNormalizeSymbol:
    """Test symbol normalization from OKX format to canonical."""

    def test_btc_usdt(self):
        assert mappers.normalize_symbol("BTC-USDT") == "BTCUSDT"

    def test_eth_usdt(self):
        assert mappers.normalize_symbol("ETH-USDT") == "ETHUSDT"

    def test_multi_char_quote(self):
        assert mappers.normalize_symbol("DOGE-USDC") == "DOGEUSDC"

    def test_no_dash(self):
        """Already normalized symbol passes through."""
        assert mappers.normalize_symbol("BTCUSDT") == "BTCUSDT"


class TestMapTicker:
    """Test OKX ticker mapping to canonical format."""

    def test_basic_ticker_mapping(self):
        raw = {
            "instId": "BTC-USDT",
            "last": "50000.5",
            "lastSz": "1.5",
            "askPx": "50001.0",
            "askSz": "2.0",
            "bidPx": "49999.5",
            "bidSz": "1.8",
            "open24h": "49000.0",
            "high24h": "50500.0",
            "low24h": "48500.0",
            "volCcy24h": "1000000.5",
            "vol24h": "20.5",
            "ts": "1609459200000",
        }
        result = mappers.map_ticker(raw)

        assert result["symbol"] == "BTCUSDT"
        assert result["exchange"] == "okx"
        assert result["close"] == 50000.5
        assert result["bid"] == 49999.5
        assert result["ask"] == 50001.0
        assert result["h24_open"] == 49000.0
        assert result["h24_high"] == 50500.0
        assert result["h24_low"] == 48500.0
        assert result["h24_volume"] == 20.5
        assert result["h24_quote_volume"] == 1000000.5
        assert result["h24_price_change"] == pytest.approx(1000.5)
        assert result["h24_price_change_pct"] == pytest.approx(2.04183673469)
        assert result["event_time"] == 1609459200000

    def test_ticker_no_change(self):
        """Zero open results in zero price change."""
        raw = {
            "instId": "ETH-USDT",
            "last": "3000.0",
            "open24h": "0",
            "ts": "1609459200000",
        }
        result = mappers.map_ticker(raw)

        assert result["h24_price_change"] == 0
        assert result["h24_price_change_pct"] == 0

    def test_ticker_missing_fields(self):
        """Missing fields default to zero."""
        raw = {
            "instId": "SOL-USDT",
            "ts": "1609459200000",
        }
        result = mappers.map_ticker(raw)

        assert result["symbol"] == "SOLUSDT"
        assert result["close"] == 0
        assert result["bid"] == 0
        assert result["ask"] == 0


class TestMapAggTrade:
    """Test OKX aggregate trade mapping."""

    def test_basic_trade_mapping(self):
        raw = {
            "instId": "BTC-USDT",
            "tradeId": "12345678",
            "px": "50000.5",
            "sz": "1.234",
            "side": "buy",
            "ts": "1609459200000",
        }
        result = mappers.map_agg_trade(raw)

        assert result["symbol"] == "BTCUSDT"
        assert result["exchange"] == "okx"
        assert result["agg_trade_id"] == 12345678
        assert result["price"] == 50000.5
        assert result["quantity"] == 1.234
        assert result["trade_time"] == 1609459200000
        assert result["is_buyer_maker"] is False  # buy = not maker

    def test_sell_side_is_maker(self):
        raw = {
            "instId": "ETH-USDT",
            "tradeId": "999",
            "px": "3000.0",
            "sz": "2.0",
            "side": "sell",
            "ts": "1609459200000",
        }
        result = mappers.map_agg_trade(raw)

        assert result["is_buyer_maker"] is True  # sell = maker is buyer


class TestMapKline:
    """Test OKX kline/candlestick mapping."""

    def test_kline_array_format(self):
        # OKX kline format: [ts, o, h, l, c, vol, volCcy, confirm]
        raw = [
            "1609459200000",  # ts
            "50000.0",        # o
            "50500.0",        # h
            "49500.0",        # l
            "50200.0",        # c
            "100.5",          # vol
            "5000000.0",      # volCcy
            "0",              # confirm (not closed)
        ]
        result = mappers.map_kline(raw)

        assert result["exchange"] == "okx"
        assert result["kline_start"] == 1609459200000
        assert result["kline_close"] == 1609459201000  # +1s for 1s interval
        assert result["interval"] == "1s"
        assert result["open"] == 50000.0
        assert result["high"] == 50500.0
        assert result["low"] == 49500.0
        assert result["close"] == 50200.0
        assert result["volume"] == 100.5
        assert result["quote_volume"] == 5000000.0
        assert result["is_closed"] is False

    def test_kline_closed_candle(self):
        raw = [
            "1609459200000",
            "50000.0",
            "50500.0",
            "49500.0",
            "50200.0",
            "100.5",
            "5000000.0",
            "1",  # closed
        ]
        result = mappers.map_kline(raw)

        assert result["is_closed"] is True

    def test_kline_dict_format(self):
        raw = {
            "instId": "BTC-USDT",
            "ts": "1609459200000",
            "o": "50000.0",
            "h": "50500.0",
            "l": "49500.0",
            "c": "50200.0",
            "vol": "100.5",
            "volCcy": "5000000.0",
            "confirm": "1",
        }
        result = mappers.map_kline(raw)

        assert result["symbol"] == "BTCUSDT"
        assert result["open"] == 50000.0


class TestMapDepth:
    """Test OKX depth/orderbook mapping."""

    def test_basic_depth_mapping(self):
        raw = {
            "asks": [
                ["50001.0", "1.5", "0", "2"],
                ["50002.0", "2.0", "0", "1"],
            ],
            "bids": [
                ["49999.0", "2.0", "0", "3"],
                ["49998.0", "1.5", "0", "2"],
            ],
            "ts": "1609459200000",
            "checksum": 123456,
        }
        result = mappers.map_depth(raw)

        assert result["exchange"] == "okx"
        assert result["last_update_id"] == 123456
        # Bids/asks stored as JSON strings
        assert "49999.0" in result["bids"]
        assert "50001.0" in result["asks"]

    def test_depth_empty_sides(self):
        raw = {
            "asks": [],
            "bids": [],
            "ts": "1609459200000",
        }
        result = mappers.map_depth(raw)

        assert result["bids"] == "[]"
        assert result["asks"] == "[]"


class TestOKXClientSubscriptionFrames:
    """Test OKX client subscription frame building."""

    def setup_method(self):
        self.client = OKXClient()

    def test_build_subscribe_frame_single(self):
        channels = [{"channel": "tickers", "instId": "BTC-USDT"}]
        frame = self.client.build_subscribe_frame(channels, "subscribe")

        parsed = json.loads(frame)
        assert parsed["op"] == "subscribe"
        assert len(parsed["args"]) == 1
        assert parsed["args"][0]["channel"] == "tickers"
        assert parsed["args"][0]["instId"] == "BTC-USDT"

    def test_build_subscribe_frame_multiple(self):
        channels = [
            {"channel": "tickers", "instId": "BTC-USDT"},
            {"channel": "tickers", "instId": "ETH-USDT"},
        ]
        frame = self.client.build_subscribe_frame(channels, "subscribe")

        parsed = json.loads(frame)
        assert len(parsed["args"]) == 2

    def test_build_unsubscribe_frame(self):
        channels = [{"channel": "tickers", "instId": "BTC-USDT"}]
        frame = self.client.build_subscribe_frame(channels, "unsubscribe")

        parsed = json.loads(frame)
        assert parsed["op"] == "unsubscribe"

    def test_build_ticker_channels(self):
        symbols = ["BTCUSDT", "ETHUSDT"]
        channels = self.client.build_ticker_channels(symbols)

        assert len(channels) == 2
        assert channels[0]["channel"] == "tickers"
        assert channels[0]["instId"] == "BTC-USDT"
        assert channels[1]["instId"] == "ETH-USDT"

    def test_build_trade_channels(self):
        symbols = ["BTCUSDT", "ETHUSDT"]
        channels = self.client.build_trade_channels(symbols)

        assert all(c["channel"] == "trades" for c in channels)
        assert channels[0]["instId"] == "BTC-USDT"

    def test_build_kline_channels_1m(self):
        symbols = ["BTCUSDT"]
        channels = self.client.build_kline_channels(symbols, "1m")

        assert channels[0]["channel"] == "candle1m"
        assert channels[0]["instId"] == "BTC-USDT"

    def test_build_kline_channels_1h(self):
        symbols = ["ETHUSDT"]
        channels = self.client.build_kline_channels(symbols, "1h")

        assert channels[0]["channel"] == "candle1H"

    def test_build_kline_channels_1d(self):
        symbols = ["DOGEUSDT"]
        channels = self.client.build_kline_channels(symbols, "1d")

        assert channels[0]["channel"] == "candle1D"

    def test_build_depth_channels(self):
        symbols = ["BTCUSDT", "ETHUSDT"]
        channels = self.client.build_depth_channels(symbols, "5")

        assert all(c["channel"] == "books5" for c in channels)

    def test_uses_subscription_frames(self):
        assert self.client.uses_subscription_frames is True

    def test_exchange_name(self):
        assert self.client.exchange_name == "okx"


class TestOKXClientStreamNames:
    """Test OKX client stream name building."""

    def setup_method(self):
        self.client = OKXClient()

    def test_trade_stream_name(self):
        name = self.client.trade_stream_name("BTCUSDT")
        assert name == "trades:BTC-USDT"

    def test_kline_stream_name_1m(self):
        name = self.client.kline_stream_name("BTCUSDT", "1m")
        assert name == "candle1m:BTC-USDT"

    def test_kline_stream_name_1h(self):
        name = self.client.kline_stream_name("ETHUSDT", "1h")
        assert name == "candle1H:ETH-USDT"

    def test_depth_stream_name(self):
        name = self.client.depth_stream_name("BTCUSDT", "5", "100ms")
        assert name == "books5:BTC-USDT"

    def test_ws_url(self):
        url = self.client.build_ticker_stream_url()
        assert url == "wss://ws.okx.com:8443/ws/v5/public"

        url = self.client.build_combined_stream_url([])
        assert url == "wss://ws.okx.com:8443/ws/v5/public"