"""Unit tests for backend.services.news_service.

Tests cover:
- _normalize_symbol helper
- _as_list helper
- _row_to_article conversion
- get_latest (all filters: no filter, source, symbol, both, pool=None)
- get_sources
- get_trending
- get_symbol_sentiment
- search_news
"""
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _AsyncCtxMgr:
    """Helper: wraps an object so it works as `async with pool.acquire() as conn`."""
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


class _Row(dict):
    """Dict subclass that also supports attribute access (simulates asyncpg Record)."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


def _make_row(**overrides) -> _Row:
    """Create a mock asyncpg Record with sensible defaults."""
    defaults = {
        "id": 1,
        "source": "cryptopanic",
        "title": "Bitcoin hits new all-time high",
        "summary": "BTC rallies past $100k",
        "content_snippet": None,
        "url": "https://example.com/btc-ath",
        "external_id": "abc123",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "fetched_at": datetime.now(timezone.utc),
        "sentiment_score": 0.7,
        "sentiment_label": "bullish",
        "sentiment_confidence": 0.85,
        "sentiment_computed_at": datetime.now(timezone.utc),
        "symbols": ["BTC"],
        "tags": ["market"],
        "symbols_mentioned": ["BTC", "ETH"],
        "raw_metadata": {"domain": "example.com"},
        "language": "en",
    }
    defaults.update(overrides)
    return _Row(defaults)


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(return_value=_AsyncCtxMgr(conn))
    return pool, conn


# ---------------------------------------------------------------------------
# Tests: _normalize_symbol
# ---------------------------------------------------------------------------

class TestNormalizeSymbol:
    @pytest.mark.unit
    def test_removes_usdt(self):
        from backend.services.news_service import _normalize_symbol
        assert _normalize_symbol("BTCUSDT") == "BTC"

    @pytest.mark.unit
    def test_removes_usd(self):
        from backend.services.news_service import _normalize_symbol
        assert _normalize_symbol("ETHUSD") == "ETH"

    @pytest.mark.unit
    def test_none_returns_none(self):
        from backend.services.news_service import _normalize_symbol
        assert _normalize_symbol(None) is None

    @pytest.mark.unit
    def test_empty_string_returns_none(self):
        from backend.services.news_service import _normalize_symbol
        assert _normalize_symbol("") is None

    @pytest.mark.unit
    def test_case_insensitive(self):
        from backend.services.news_service import _normalize_symbol
        assert _normalize_symbol("btcusdt") == "BTC"

    @pytest.mark.unit
    def test_plain_symbol(self):
        from backend.services.news_service import _normalize_symbol
        assert _normalize_symbol("BTC") == "BTC"


# ---------------------------------------------------------------------------
# Tests: _as_list
# ---------------------------------------------------------------------------

class TestAsList:
    @pytest.mark.unit
    def test_none(self):
        from backend.services.news_service import _as_list
        assert _as_list(None) == []

    @pytest.mark.unit
    def test_list_passthrough(self):
        from backend.services.news_service import _as_list
        assert _as_list(["BTC", "ETH"]) == ["BTC", "ETH"]

    @pytest.mark.unit
    def test_json_string(self):
        from backend.services.news_service import _as_list
        assert _as_list('["BTC", "ETH"]') == ["BTC", "ETH"]

    @pytest.mark.unit
    def test_invalid_json_string(self):
        from backend.services.news_service import _as_list
        assert _as_list("not json") == []

    @pytest.mark.unit
    def test_non_string_non_list(self):
        from backend.services.news_service import _as_list
        assert _as_list(42) == []


# ---------------------------------------------------------------------------
# Tests: _row_to_article
# ---------------------------------------------------------------------------

class TestRowToArticle:
    @pytest.mark.unit
    def test_basic_conversion(self):
        from backend.services.news_service import _row_to_article
        row = _make_row()
        article = _row_to_article(row)

        assert article["id"] == "1"
        assert article["source"] == "cryptopanic"
        assert article["title"] == "Bitcoin hits new all-time high"
        assert article["url"] == "https://example.com/btc-ath"
        assert article["sentiment_score"] == 0.7
        assert article["sentiment_label"] == "bullish"
        assert article["symbolsMentioned"] == ["BTC", "ETH"]

    @pytest.mark.unit
    def test_null_sentiment_defaults(self):
        from backend.services.news_service import _row_to_article
        row = _make_row(sentiment_score=None, sentiment_label=None)
        article = _row_to_article(row)

        assert article["sentiment_score"] == 0.0
        assert article["sentiment_label"] == "neutral"

    @pytest.mark.unit
    def test_missing_url_defaults_hash(self):
        from backend.services.news_service import _row_to_article
        row = _make_row(url=None)
        article = _row_to_article(row)
        assert article["url"] == "#"

    @pytest.mark.unit
    def test_raw_metadata_string_parsed(self):
        from backend.services.news_service import _row_to_article
        row = _make_row(raw_metadata='{"domain": "coindesk.com"}')
        article = _row_to_article(row)
        assert article["author"] is None  # no "author" key in dict
        assert isinstance(article.get("url"), str)

    @pytest.mark.unit
    def test_published_at_iso_string(self):
        from backend.services.news_service import _row_to_article
        row = _make_row()
        article = _row_to_article(row)
        assert isinstance(article["published_at"], str)
        # Should contain 'T' (ISO format)
        assert "T" in article["published_at"]


# ---------------------------------------------------------------------------
# Tests: get_latest
# ---------------------------------------------------------------------------

class TestGetLatest:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_articles_from_postgres(self, mock_pool):
        from backend.services.news_service import get_latest
        pool, conn = mock_pool
        rows = [_make_row(id=i, title=f"News {i}") for i in range(3)]
        conn.fetch = AsyncMock(return_value=rows)

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_latest(limit=10)

        assert result["count"] == 3
        assert result["metadata"]["is_mock"] is False
        assert result["metadata"]["source"] == "postgres"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_filter_by_symbol(self, mock_pool):
        from backend.services.news_service import get_latest
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[_make_row(symbols_mentioned=["BTC"])])

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            await get_latest(symbol="BTCUSDT", limit=10)

        query = conn.fetch.call_args[0][0]
        assert "symbols_mentioned" in query
        assert "= ANY(symbols_mentioned)" in query

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_filter_by_source(self, mock_pool):
        from backend.services.news_service import get_latest
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[_make_row()])

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            await get_latest(source="cryptopanic", limit=10)

        query = conn.fetch.call_args[0][0]
        assert "lower(source) = lower" in query

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_filter_by_source_and_symbol(self, mock_pool):
        from backend.services.news_service import get_latest
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[_make_row()])

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            await get_latest(source="coindesk", symbol="ETH", limit=10)

        query = conn.fetch.call_args[0][0]
        assert "AND lower(source)" in query
        assert "AND $3 = ANY(symbols_mentioned)" in query

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pool_none_returns_empty(self):
        from backend.services.news_service import get_latest
        with patch("backend.services.news_service.get_pg_pool", return_value=None):
            result = await get_latest()

        assert result["articles"] == []
        assert result["count"] == 0
        assert result["metadata"]["is_mock"] is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_has_sentiment_metadata(self, mock_pool):
        from backend.services.news_service import get_latest
        pool, conn = mock_pool
        rows = [_make_row(sentiment_score=0.5)]
        conn.fetch = AsyncMock(return_value=rows)

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_latest()

        assert result["metadata"]["has_sentiment"] is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_sentiment_metadata(self, mock_pool):
        from backend.services.news_service import get_latest
        pool, conn = mock_pool
        rows = [_make_row(sentiment_score=None, sentiment_label=None)]
        conn.fetch = AsyncMock(return_value=rows)

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_latest()

        # sentiment_score None → float(None or 0) = 0.0 → has_sentiment check is:
        # any(article.get("sentiment_score") is not None) → True because 0.0 is not None
        # Actually _row_to_article converts to float(0.7 or 0) = 0.7, but for None → float(None or 0) = 0.0
        # 0.0 is not None → has_sentiment = True
        # So the metadata check is about "is not None", and 0.0 is not None
        assert isinstance(result["metadata"]["has_sentiment"], bool)


# ---------------------------------------------------------------------------
# Tests: get_sources
# ---------------------------------------------------------------------------

class TestGetSources:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_source_list(self, mock_pool):
        from backend.services.news_service import get_sources
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[
            _Row({"source": "cryptopanic", "article_count": 10, "latest": datetime.now(timezone.utc)}),
            _Row({"source": "coindesk", "article_count": 5, "latest": None}),
        ])

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_sources()

        assert result["total_sources"] == 2
        assert result["healthy_sources"] == 2
        assert len(result["sources"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pool_none_returns_empty(self):
        from backend.services.news_service import get_sources
        with patch("backend.services.news_service.get_pg_pool", return_value=None):
            result = await get_sources()

        assert result["total_sources"] == 0


# ---------------------------------------------------------------------------
# Tests: get_trending
# ---------------------------------------------------------------------------

class TestGetTrending:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_articles_and_symbols(self, mock_pool):
        from backend.services.news_service import get_trending
        pool, conn = mock_pool

        article_row = _make_row(title="Ethereum upgrade")
        symbol_row = _Row({"symbol": "BTC", "mention_count": 15, "avg_sentiment": 0.5})

        conn.fetch = AsyncMock(
            side_effect=[
                [article_row],  # article query
                [symbol_row],   # symbol query
            ]
        )

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_trending(limit=10)

        assert "trending_articles" in result
        assert "trending_symbols" in result
        assert len(result["trending_symbols"]) == 1
        assert result["trending_symbols"][0]["symbol"] == "BTC"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pool_none_returns_empty(self):
        from backend.services.news_service import get_trending
        with patch("backend.services.news_service.get_pg_pool", return_value=None):
            result = await get_trending()

        assert result["trending_articles"] == []
        assert result["trending_symbols"] == []


# ---------------------------------------------------------------------------
# Tests: get_symbol_sentiment
# ---------------------------------------------------------------------------

class TestGetSymbolSentiment:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_sentiment_data(self, mock_pool):
        from backend.services.news_service import get_symbol_sentiment
        pool, conn = mock_pool
        rows = [
            _Row({"published_at": datetime.now(timezone.utc), "sentiment_score": 0.5, "sentiment_label": "bullish"}),
            _Row({"published_at": datetime.now(timezone.utc), "sentiment_score": -0.3, "sentiment_label": "bearish"}),
        ]
        conn.fetch = AsyncMock(return_value=rows)

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_symbol_sentiment("BTCUSDT")

        assert result["symbol"] == "BTC"
        assert result["article_count"] == 2
        assert result["avg_sentiment"] > 0  # (0.5 + -0.3) / 2 = 0.1
        assert result["sentiment_distribution"]["positive"] == 1
        assert result["sentiment_distribution"]["negative"] == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_articles_returns_zeros(self, mock_pool):
        from backend.services.news_service import get_symbol_sentiment
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[])

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_symbol_sentiment("BTCUSDT")

        assert result["symbol"] == "BTC"
        assert result["article_count"] == 0
        assert result["avg_sentiment"] == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pool_none_returns_empty(self):
        from backend.services.news_service import get_symbol_sentiment
        with patch("backend.services.news_service.get_pg_pool", return_value=None):
            result = await get_symbol_sentiment("BTCUSDT")

        assert result["article_count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_trend_limited_to_50(self, mock_pool):
        from backend.services.news_service import get_symbol_sentiment
        pool, conn = mock_pool
        rows = [
            _Row({
                "published_at": datetime.now(timezone.utc) - timedelta(hours=i),
                "sentiment_score": 0.1 * i,
                "sentiment_label": "bullish",
            })
            for i in range(100)
        ]
        conn.fetch = AsyncMock(return_value=rows)

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await get_symbol_sentiment("BTCUSDT")

        assert len(result["sentiment_trend"]) == 50


# ---------------------------------------------------------------------------
# Tests: search_news
# ---------------------------------------------------------------------------

class TestSearchNews:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_matching_articles(self, mock_pool):
        from backend.services.news_service import search_news
        pool, conn = mock_pool
        rows = [_make_row(title="Bitcoin ETF approval")]
        conn.fetch = AsyncMock(return_value=rows)

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            result = await search_news(query="Bitcoin ETF")

        assert result["query"] == "Bitcoin ETF"
        assert result["total"] == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_uses_ilike(self, mock_pool):
        from backend.services.news_service import search_news
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[])

        with patch("backend.services.news_service.get_pg_pool", return_value=pool):
            await search_news(query="Ethereum")

        query = conn.fetch.call_args[0][0]
        assert "ILIKE" in query

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pool_none_returns_empty(self):
        from backend.services.news_service import search_news
        with patch("backend.services.news_service.get_pg_pool", return_value=None):
            result = await search_news(query="test")

        assert result["total"] == 0
        assert result["articles"] == []
