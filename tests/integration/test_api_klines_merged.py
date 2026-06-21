"""
Integration tests for the merged klines endpoint.

Covers ``GET /api/merged/{symbol}`` which returns the latest closed
candles from the Redis sorted set plus a live forming candle derived
from the most recent ticker price.

Branches exercised:

* ``same_minute`` — closed candle timestamp equals the ticker's minute
  → forming inherits the closed open/high/low/volume and updates
  high/low/close with the live price.
* ``new_minute`` — ticker event landed in a later minute than the
  newest closed candle → forming opens at the live price with zero
  volume.
* ``no_closed`` — no closed candles yet → return only the forming
  candle.
* ``ticker_missing`` — no ticker hash → return closed only.
* ``ticker_zero_price`` — ticker price == 0 → return closed only.
* ``validation`` — invalid interval / out-of-range limit / missing
  path param surface 4xx instead of 5xx.

Run with::

    PYTHONPATH=. python -m pytest tests/integration/test_api_klines_merged.py -v
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app import app


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_mock_redis(zset_data=None, ticker_data=None) -> AsyncMock:
    """Build a Redis mock that serves zset + ticker responses.

    ``zset_data`` maps ``candle:1m:binance:<sym>`` to a list of
    ``(member_bytes, score_ms)`` tuples that mimics what
    ``ZREVRANGEBYSCORE … WITHSCORES`` returns.

    ``ticker_data`` maps ``ticker:latest:binance:<sym>`` to a dict of
    stringified fields mimicking ``HGETALL``.
    """

    r = AsyncMock()
    r.zset_data = zset_data or {}
    r.ticker_data = ticker_data or {}

    async def mock_zrevrangebyscore(key, max_score, min_score, withscores=False, start=None, num=None):
        return r.zset_data.get(key, [])

    async def mock_hgetall(key):
        data = r.ticker_data.get(key, {})
        # Mirror redis-py async behaviour: returns bytes
        return {k.encode(): v.encode() for k, v in data.items()}

    r.zrevrangebyscore = AsyncMock(side_effect=mock_zrevrangebyscore)
    r.hgetall = AsyncMock(side_effect=mock_hgetall)
    return r


def _closed_member(symbol: str, ts_ms: int, o: float, h: float, lo: float, c: float, v: float, qv: float = 0.0, tc: int = 0):
    """Serialize a closed candle the way binance-kline-rest writes it."""
    payload = {
        "open": o, "high": h, "low": lo, "close": c,
        "volume": v, "quote_volume": qv, "trade_count": tc,
        "symbol": symbol, "interval": "1m",
    }
    return (json.dumps(payload).encode(), ts_ms)


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestMergedKlinesEndpoint:

    @pytest.mark.asyncio
    async def test_same_minute_forming_inherits_open_and_extremes(self):
        """Ticker event falls inside the latest closed candle's minute.

        Forming candle inherits open/volume from the closed candle and
        updates high/low/close with the live ticker price.
        """
        minute_ts = 1_700_000_000_000  # minute-aligned
        event_ts = minute_ts + 30_000  # 30 s into the same minute

        zset_data = {
            "candle:1m:binance:btcusdt": [
                _closed_member("btcusdt", minute_ts, 100.0, 101.0, 99.5, 100.5, 12.5, qv=1250.0, tc=42),
                _closed_member("btcusdt", minute_ts - 60_000, 99.0, 100.0, 98.5, 99.5, 11.0),
            ],
        }
        ticker_data = {
            "ticker:latest:binance:btcusdt": {
                "price": "102.0",       # above closed.high (101) → new high
                "event_time": str(event_ts),
            },
        }
        mock_r = _make_mock_redis(zset_data, ticker_data)

        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/btcusdt")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        forming = data[0]
        assert forming["timestamp"] == minute_ts
        assert forming["open"] == 100.0          # inherited
        assert forming["high"] == 102.0          # max(101.0, 102.0)
        assert forming["low"] == 99.5            # min(99.5, 102.0)
        assert forming["close"] == 102.0         # live price
        assert forming["volume"] == 12.5         # inherited
        assert forming["quote_volume"] == 1250.0
        assert forming["trade_count"] == 42
        assert forming["isClosed"] is False

        # Second entry is the prior closed candle
        assert data[1]["timestamp"] == minute_ts - 60_000
        assert data[1]["isClosed"] is True

    @pytest.mark.asyncio
    async def test_new_minute_forming_opens_at_live_price(self):
        """Ticker event landed in a minute later than the newest closed candle."""
        latest_closed_ts = 1_700_000_000_000  # minute T
        event_ts = latest_closed_ts + 90_000  # minute T+1 (90 s in)

        zset_data = {
            "candle:1m:binance:btcusdt": [
                _closed_member("btcusdt", latest_closed_ts, 100.0, 101.0, 99.5, 100.5, 12.5),
            ],
        }
        ticker_data = {
            "ticker:latest:binance:btcusdt": {
                "price": "105.0",
                "event_time": str(event_ts),
            },
        }
        mock_r = _make_mock_redis(zset_data, ticker_data)

        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/btcusdt")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        forming = data[0]
        assert forming["timestamp"] == latest_closed_ts + 60_000
        assert forming["open"] == 105.0
        assert forming["high"] == 105.0
        assert forming["low"] == 105.0
        assert forming["close"] == 105.0
        assert forming["volume"] == 0
        assert forming["isClosed"] is False

    @pytest.mark.asyncio
    async def test_no_closed_only_forming(self):
        """No closed candles in zset → return only the forming candle."""
        event_ts = 1_700_000_090_000  # already minute-aligned
        ticker_data = {
            "ticker:latest:binance:ethusdt": {
                "price": "2000.0",
                "event_time": str(event_ts),
            },
        }
        mock_r = _make_mock_redis(zset_data={}, ticker_data=ticker_data)

        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/ethusdt")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        forming = data[0]
        assert forming["timestamp"] == event_ts
        assert forming["open"] == forming["close"] == 2000.0
        assert forming["isClosed"] is False

    @pytest.mark.asyncio
    async def test_missing_ticker_returns_closed_only(self):
        """Ticker hash absent → return the closed candles untouched."""
        zset_data = {
            "candle:1m:binance:btcusdt": [
                _closed_member("btcusdt", 1_700_000_000_000, 100.0, 101.0, 99.5, 100.5, 12.5),
            ],
        }
        mock_r = _make_mock_redis(zset_data, ticker_data={})

        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/btcusdt")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["isClosed"] is True
        assert data[0]["timestamp"] == 1_700_000_000_000

    @pytest.mark.asyncio
    async def test_ticker_zero_price_returns_closed_only(self):
        """Ticker price == 0 (degenerate) → skip forming candle."""
        zset_data = {
            "candle:1m:binance:btcusdt": [
                _closed_member("btcusdt", 1_700_000_000_000, 100.0, 101.0, 99.5, 100.5, 12.5),
            ],
        }
        ticker_data = {
            "ticker:latest:binance:btcusdt": {
                "price": "0",
                "event_time": str(1_700_000_030_000),
            },
        }
        mock_r = _make_mock_redis(zset_data, ticker_data)

        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/btcusdt")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["isClosed"] is True

    @pytest.mark.asyncio
    async def test_limit_truncates_to_requested_window(self):
        """Passing limit=2 returns at most 2 candles even when zset has more."""
        zset_data = {
            "candle:1m:binance:btcusdt": [
                _closed_member("btcusdt", 1_700_000_120_000, 110.0, 111.0, 109.5, 110.5, 12.0),
                _closed_member("btcusdt", 1_700_000_060_000, 109.0, 110.0, 108.5, 109.5, 11.0),
                _closed_member("btcusdt", 1_700_000_000_000, 108.0, 109.0, 107.5, 108.5, 10.0),
            ],
        }
        mock_r = _make_mock_redis(zset_data, ticker_data={})

        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/btcusdt?limit=2")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_invalid_interval_returns_422(self):
        """Out-of-spec interval is rejected by FastAPI's Query validator."""
        mock_r = _make_mock_redis()
        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/btcusdt?interval=3m")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_limit_too_high_returns_422(self):
        mock_r = _make_mock_redis()
        with patch("backend.api.klines.get_redis", return_value=mock_r):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/merged/btcusdt?limit=1001")
        assert resp.status_code == 422
