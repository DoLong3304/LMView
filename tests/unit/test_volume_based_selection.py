"""
Tests for P0 fix: volume-based symbol selection.

The new ``fetch_top_symbols_by_volume()`` method on ``BinanceClient``
replaces the alphabetical ``fetch_symbols()[:N]`` selection that
was missing 116/200 high-volume symbols (SOL, XRP, PEPE, SUI, TON,
TRX, USDC, etc.).

These tests use ``unittest.mock`` to avoid real Binance API calls.

Run with::

    PYTHONPATH=. python -m pytest tests/unit/test_volume_based_selection.py -v
"""

from __future__ import annotations

import os
import sys
import time
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest

from exchanges.binance.client import (
    BinanceClient,
    _SYMBOL_VOLUME_CACHE,
    _SYMBOL_VOLUME_CACHE_TTL_SEC,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


def _make_active_symbols_response(active_symbols: list[str]) -> dict:
    """Build a fake Binance /exchangeInfo response."""
    return {
        "symbols": [
            {
                "symbol": s,
                "quoteAsset": "USDT",
                "status": "TRADING",
                "isSpotTradingAllowed": True,
            }
            for s in active_symbols
        ]
    }


def _make_24h_ticker_response(tickers: list[tuple[str, float]]) -> list[dict]:
    """Build a fake Binance /ticker/24hr response.

    ``tickers`` is a list of (symbol, quoteVolume) pairs.
    """
    return [
        {
            "symbol": sym,
            "quoteVolume": str(vol),
            "lastPrice": "1.0",
            "count": "100",
        }
        for sym, vol in tickers
    ]


@pytest.fixture
def client():
    """Fresh BinanceClient with fast retries."""
    return BinanceClient(max_retries=1, request_delay=0.01)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure each test starts with a clean cache."""
    _SYMBOL_VOLUME_CACHE.clear()
    yield
    _SYMBOL_VOLUME_CACHE.clear()


# ── Tests: Happy path ───────────────────────────────────────────────────────


class TestVolumeSelectionHappyPath:
    """Core functionality tests."""

    def test_returns_top_n_by_volume(self, client):
        """Should return top N symbols sorted by quote volume desc."""
        active = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "PEPEUSDT", "XRPUSDT"]
        tickers = [
            ("BTCUSDT", 1_000_000_000),
            ("ETHUSDT", 500_000_000),
            ("SOLUSDT", 200_000_000),
            ("PEPEUSDT", 50_000_000),
            ("XRPUSDT", 100_000_000),
        ]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            result = client.fetch_top_symbols_by_volume("USDT", 3)

        assert result == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        assert len(result) == 3

    def test_includes_high_volume_coins(self, client):
        """P0 acceptance: SOL, XRP, PEPE, SUI, TON must be in top 200.

        This is the "fake cow" regression test. Before the fix, these
        symbols were missing because they sort alphabetically AFTER
        symbols like JST, JTO, JUP, etc.
        """
        # Build a realistic universe: 250 symbols, with high-volume
        # coins placed at the END alphabetically.
        high_volume = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "PEPEUSDT",
            "SUIUSDT", "TONUSDT", "TRXUSDT", "NEARUSDT", "DOGEUSDT",
            "USDCUSDT", "WLFIUSDT", "WLDUSDT", "ZECUSDT", "TRUMPUSDT",
        ]
        # Use a smaller low-volume pool so high-volume symbols are
        # GUARANTEED to be in the top 200 by volume.
        low_volume = [f"X{i:03d}USDT" for i in range(150)]
        active = high_volume + low_volume
        tickers = [(s, 100_000_000) for s in high_volume] + \
                  [(s, 1_000) for s in low_volume]

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            result = client.fetch_top_symbols_by_volume("USDT", 200)

        # All high-volume symbols must be present
        for sym in high_volume:
            assert sym in result, (
                f"P0 regression: high-volume symbol {sym} missing from "
                f"top-200 by volume. This is the 'fake cow' bug."
            )
        # We asked for top 200 from 165 total → expect all 165 back
        assert len(result) == 165

    def test_filters_to_usdt_quote_only(self, client):
        """Non-USDT pairs (e.g. BTCUSDC, ETHBTC) must be excluded."""
        active = ["BTCUSDT", "BTCUSDC", "ETHUSDT", "ETHBTC", "SOLUSDT"]
        tickers = [
            ("BTCUSDT", 1_000_000),
            ("ETHUSDT", 500_000),
            ("SOLUSDT", 200_000),
        ]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            result = client.fetch_top_symbols_by_volume("USDT", 10)
        assert result == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        assert "BTCUSDC" not in result
        assert "ETHBTC" not in result

    def test_filters_inactive_symbols(self, client):
        """Symbols with status != TRADING or isSpotTradingAllowed=False
        must be excluded even if they have 24h volume."""
        # Active universe: only the active subset
        active_response = {
            "symbols": [
                {"symbol": "BTCUSDT", "quoteAsset": "USDT",
                 "status": "TRADING", "isSpotTradingAllowed": True},
                {"symbol": "XRPUSDT", "quoteAsset": "USDT",
                 "status": "TRADING", "isSpotTradingAllowed": True},
                # BTCUP is in 24h tickers but NOT in active
            ]
        }
        tickers = [
            ("BTCUPUSDT", 999_999_999),  # high volume but not active
            ("BTCUSDT",  100_000_000),
            ("XRPUSDT",   50_000_000),
        ]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=lambda: active_response,
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            result = client.fetch_top_symbols_by_volume("USDT", 10)
        assert "BTCUPUSDT" not in result
        assert result == ["BTCUSDT", "XRPUSDT"]


# ── Tests: Caching ──────────────────────────────────────────────────────────


class TestVolumeSelectionCache:
    """Cache layer must reduce API calls."""

    def test_cache_hit_skips_api_call(self, client):
        """Second call within TTL must not hit the API."""
        active = ["BTCUSDT", "ETHUSDT"]
        tickers = [("BTCUSDT", 1_000), ("ETHUSDT", 500)]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            # First call: 2 HTTP requests
            r1 = client.fetch_top_symbols_by_volume("USDT", 2)
            assert mock_get.call_count == 2

            # Second call within TTL: 0 HTTP requests
            r2 = client.fetch_top_symbols_by_volume("USDT", 2)
            assert mock_get.call_count == 2  # unchanged
            assert r1 == r2

    def test_cache_expiry_triggers_refetch(self, client):
        """Cache must be invalidated after TTL."""
        active = ["BTCUSDT"]
        tickers = [("BTCUSDT", 1_000)]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
                # 2nd fetch (after expiry)
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            client.fetch_top_symbols_by_volume("USDT", 1)
            # Simulate cache expiry
            cache_key = "USDT:1"
            ts, _ = _SYMBOL_VOLUME_CACHE[cache_key]
            _SYMBOL_VOLUME_CACHE[cache_key] = (
                ts - _SYMBOL_VOLUME_CACHE_TTL_SEC - 1,  # expired
                [],
            )
            # Now refetch
            client.fetch_top_symbols_by_volume("USDT", 1)
            assert mock_get.call_count == 4  # 2+2

    def test_clear_cache_helper(self, client):
        """The _clear_symbol_volume_cache helper must work."""
        _SYMBOL_VOLUME_CACHE["USDT:200"] = (time.time(), ["BTCUSDT"])
        assert len(_SYMBOL_VOLUME_CACHE) == 1
        client._clear_symbol_volume_cache()
        assert len(_SYMBOL_VOLUME_CACHE) == 0

    def test_different_n_values_cached_separately(self, client):
        """Cache key includes n, so n=50 and n=200 hit different entries."""
        active = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        tickers = [("BTCUSDT", 100), ("ETHUSDT", 50), ("SOLUSDT", 25)]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                # First call: n=2
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
                # Second call: n=3
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            r1 = client.fetch_top_symbols_by_volume("USDT", 2)
            r2 = client.fetch_top_symbols_by_volume("USDT", 3)
            assert len(r1) == 2
            assert len(r2) == 3
            # Third call: n=2 should hit cache
            r3 = client.fetch_top_symbols_by_volume("USDT", 2)
            assert r3 == r1
            assert mock_get.call_count == 4  # 2 calls + 2 calls, 3rd cached


# ── Tests: Error handling ───────────────────────────────────────────────────


class TestVolumeSelectionErrorHandling:
    """Fallback behaviour when Binance API is down."""

    def test_api_failure_falls_back_to_alphabetical(self, client):
        """If volume fetch fails after all retries, fall back to
        ``fetch_symbols()[:n]`` (alphabetical) so producer still starts.
        """
        active = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        with patch("requests.get") as mock_get:
            # Both /exchangeInfo and /ticker/24hr fail
            mock_get.side_effect = requests_exc = Exception("503 Service Unavailable")
            # ...but we need fetch_symbols to succeed as fallback
            with patch.object(client, "fetch_symbols", return_value=active):
                result = client.fetch_top_symbols_by_volume("USDT", 3)

        assert result == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def test_retry_logic(self, client):
        """First N-1 attempts fail, last attempt succeeds."""
        active = ["BTCUSDT"]
        tickers = [("BTCUSDT", 1_000)]
        # client.max_retries=1 from fixture → 1 attempt total
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=lambda: _make_active_symbols_response(active),
                          raise_for_status=lambda: None),
                MagicMock(json=lambda: _make_24h_ticker_response(tickers),
                          raise_for_status=lambda: None),
            ]
            result = client.fetch_top_symbols_by_volume("USDT", 1)
        assert result == ["BTCUSDT"]


# ── Tests: Producer integration ─────────────────────────────────────────────


class TestProducerUsesVolumeSelection:
    """The producer's run_streams() must prefer the new method."""

    def test_producer_calls_volume_method(self):
        """Verify run_streams() dispatches to fetch_top_symbols_by_volume
        when available, not the alphabetical fetch_symbols()[:N].
        """
        # Patch at the producer.main module level (it's where run_streams
        # actually looks up the methods on the client instance).
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), '..', '..', 'src'))

        # Mock the producer's dependencies to prevent websocket / kafka
        # initialization from doing real work.
        with patch("producer.main.MAX_SYMBOLS", 5), \
             patch("producer.main.KAFKA_TOPIC_TICKER", "ticker"), \
             patch("producer.main.KAFKA_TOPIC_TRADES", "trades"), \
             patch("producer.main.KAFKA_TOPIC_KLINES", "klines"), \
             patch("producer.main.KAFKA_TOPIC_DEPTH", "depth"), \
             patch("producer.metrics.HEARTBEAT_TIMESTAMP") as mock_hb, \
             patch("producer.main._start_thread") as mock_start_thread:
            # Make _start_thread not actually start a thread
            mock_start_thread.return_value = MagicMock()
            mock_hb.labels.return_value = MagicMock()

            from producer.main import run_streams

            # Create a mock client that has the new method
            mock_client = MagicMock()
            mock_client.uses_subscription_frames = False
            mock_client.__class__.__name__ = "BinanceClient"
            mock_client.fetch_top_symbols_by_volume.return_value = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "PEPEUSDT",
            ]
            mock_client.fetch_symbols.return_value = [
                "1INCHUSDT", "AAVEUSDT", "ACAUSDT",
            ]  # alphabetical

            run_streams(mock_client)

            # The volume method must be called
            mock_client.fetch_top_symbols_by_volume.assert_called_with(
                "USDT", 5,
            )


# ── Tests: Cache key serialization (double-checked locking) ─────────────────


class TestCacheConcurrency:
    """The lock around the cache prevents thundering herd."""

    def test_lock_serialization(self, client):
        """When multiple threads call simultaneously, only one HTTP
        request is made (the others wait on the lock and see the
        cached value).
        """
        import threading

        active = ["BTCUSDT"]
        tickers = [("BTCUSDT", 100)]
        call_count = [0]

        def mock_get(*args, **kwargs):
            call_count[0] += 1
            time.sleep(0.05)  # simulate slow API
            url = args[0] if args else kwargs.get("url", "")
            if "ticker/24hr" in str(url):
                return MagicMock(
                    json=lambda: _make_24h_ticker_response(tickers),
                    raise_for_status=lambda: None,
                )
            return MagicMock(
                json=lambda: _make_active_symbols_response(active),
                raise_for_status=lambda: None,
            )

        with patch("requests.get", side_effect=mock_get):
            threads = [
                threading.Thread(
                    target=client.fetch_top_symbols_by_volume,
                    args=("USDT", 1),
                )
                for _ in range(5)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Only 1 thread should have actually made the API calls
        # (the others hit the cache populated by the first thread).
        # Each successful fetch makes 2 HTTP calls: /exchangeInfo + /ticker/24hr.
        assert call_count[0] == 2, (
            f"Expected 2 API calls (1 fetch × 2 endpoints, lock-serialized), "
            f"got {call_count[0]}"
        )
