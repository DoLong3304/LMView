import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

from ai_service.context.news_context import (
    build_news_context,
    _rank_articles,
    _compute_sentiment_summary,
    _compute_freshness,
    _generate_caveats,
    _normalize_symbol,
    _deduplicate_articles,
    _identify_risk_events,
    _extract_top_headlines,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_article(
    title: str = "Test Article",
    source: str = "coindesk",
    sentiment_score: float = 0.2,
    sentiment_label: str = "positive",
    symbols_mentioned: Optional[List[str]] = None,
    age_hours: float = 1.0,
    article_id: Optional[str] = None,
) -> dict:
    pub = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return {
        "id": article_id or f"test-{hash(title)}",
        "title": title,
        "source": source,
        "summary": f"Summary of {title}",
        "content_snippet": "snippet",
        "published_at": pub,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "sentiment_confidence": 0.8,
        "symbols_mentioned": symbols_mentioned or ["BTC"],
        "url": "https://example.com/article",
    }


# ── Unit tests for helpers ────────────────────────────────────────────────────

class TestNormalizeSymbol:
    def test_btcusdt(self):
        assert _normalize_symbol("BTCUSDT") == "BTC"

    def test_ethusdt(self):
        assert _normalize_symbol("ETHUSDT") == "ETH"

    def test_btcusd(self):
        assert _normalize_symbol("BTCUSD") == "BTC"

    def test_already_base(self):
        assert _normalize_symbol("BTC") == "BTC"

    def test_none(self):
        assert _normalize_symbol(None) is None

    def test_empty(self):
        assert _normalize_symbol("") is None


class TestDeduplicateArticles:
    def test_no_duplicates(self):
        a1 = _make_article(title="A", article_id="1")
        a2 = _make_article(title="B", article_id="2")
        result = _deduplicate_articles([a1], [a2])
        assert len(result) == 2

    def test_removes_duplicates(self):
        a1 = _make_article(title="A", article_id="1")
        a2 = _make_article(title="A dup", article_id="1")
        result = _deduplicate_articles([a1], [a2])
        assert len(result) == 1


class TestRankArticles:
    def test_symbol_match_ranks_higher(self):
        sym_match = _make_article(title="BTC surges", symbols_mentioned=["BTC"], age_hours=1)
        no_match = _make_article(title="ETH rises", symbols_mentioned=["ETH"], age_hours=1)
        ranked = _rank_articles([no_match, sym_match], target_symbol="BTC", query=None)
        assert ranked[0]["title"] == "BTC surges"

    def test_recency_ranks_higher(self):
        recent = _make_article(title="Recent", age_hours=0.5)
        old = _make_article(title="Old", age_hours=20)
        ranked = _rank_articles([old, recent], target_symbol=None, query=None)
        assert ranked[0]["title"] == "Recent"

    def test_query_keyword_boosts(self):
        relevant = _make_article(title="Bitcoin crash prediction")
        irrelevant = _make_article(title="Ethereum upgrade news")
        ranked = _rank_articles(
            [irrelevant, relevant],
            target_symbol=None,
            query="bitcoin crash",
        )
        assert ranked[0]["title"] == "Bitcoin crash prediction"

    def test_reliable_source_ranks_higher(self):
        reliable = _make_article(title="A", source="coindesk", age_hours=5)
        unreliable = _make_article(title="B", source="unknown_blog", age_hours=5)
        ranked = _rank_articles([unreliable, reliable], target_symbol=None, query=None)
        assert ranked[0]["source"] == "coindesk"


class TestSentimentSummary:
    def test_bullish_direction(self):
        articles = [
            _make_article(sentiment_score=0.5),
            _make_article(sentiment_score=0.3),
            _make_article(sentiment_score=0.2),
        ]
        summary = _compute_sentiment_summary(articles, "BTC")
        assert summary["direction"] == "bullish"
        assert summary["positive_count"] == 3

    def test_bearish_direction(self):
        articles = [
            _make_article(sentiment_score=-0.5),
            _make_article(sentiment_score=-0.3),
            _make_article(sentiment_score=-0.2),
        ]
        summary = _compute_sentiment_summary(articles, "BTC")
        assert summary["direction"] == "bearish"
        assert summary["negative_count"] == 3

    def test_neutral_direction(self):
        articles = [
            _make_article(sentiment_score=0.01),
            _make_article(sentiment_score=-0.01),
        ]
        summary = _compute_sentiment_summary(articles, None)
        assert summary["direction"] == "neutral"

    def test_empty_articles(self):
        summary = _compute_sentiment_summary([], None)
        assert summary["direction"] == "neutral"
        assert summary["confidence"] == "none"


class TestFreshness:
    def test_fresh_articles(self):
        articles = [_make_article(age_hours=1)]
        freshness = _compute_freshness(articles)
        assert freshness["is_stale"] is False
        assert freshness["newest_age_hours"] < 2

    def test_stale_articles(self):
        articles = [_make_article(age_hours=15)]
        freshness = _compute_freshness(articles)
        assert freshness["is_stale"] is True

    def test_no_articles(self):
        freshness = _compute_freshness([])
        assert freshness["is_stale"] is True
        assert freshness["newest_age_hours"] is None


class TestCaveats:
    def test_no_articles_caveat(self):
        caveats = _generate_caveats([], "BTC", {"is_stale": True}, {"confidence": "none"})
        assert any("No relevant news" in c for c in caveats)

    def test_sparse_articles_caveat(self):
        articles = [_make_article(), _make_article(title="B", article_id="b")]
        caveats = _generate_caveats(
            articles, "BTC",
            {"is_stale": False, "newest_age_hours": 1},
            {"confidence": "low"},
        )
        assert any("2 article" in c for c in caveats)

    def test_stale_news_caveat(self):
        articles = [_make_article(age_hours=15)] * 5
        caveats = _generate_caveats(
            articles, "BTC",
            {"is_stale": True, "newest_age_hours": 15},
            {"confidence": "low"},
        )
        assert any("15h old" in c for c in caveats)

    def test_safety_caveat_always_included(self):
        articles = [_make_article()] * 5
        caveats = _generate_caveats(
            articles, "BTC",
            {"is_stale": False, "newest_age_hours": 1},
            {"confidence": "moderate"},
        )
        assert any("not a trading signal" in c for c in caveats)


class TestRiskEvents:
    def test_detects_hack(self):
        articles = [_make_article(
            title="Major Exchange Hacked: $100M stolen",
            symbols_mentioned=["BTC"],
            sentiment_score=-0.8,
        )]
        events = _identify_risk_events(articles, "BTC")
        assert len(events) >= 1
        assert "Hacked" in events[0]

    def test_ignores_irrelevant_symbol(self):
        articles = [_make_article(
            title="ETH regulation ban",
            symbols_mentioned=["ETH"],
            sentiment_score=-0.2,
        )]
        events = _identify_risk_events(articles, "BTC")
        assert len(events) == 0

    def test_strong_market_wide_event(self):
        articles = [_make_article(
            title="Global crypto crash imminent",
            symbols_mentioned=[],
            sentiment_score=-0.9,
        )]
        events = _identify_risk_events(articles, "BTC")
        assert len(events) >= 1


class TestExtractHeadlines:
    def test_extracts_fields(self):
        articles = [_make_article(title="Test headline")]
        headlines = _extract_top_headlines(articles)
        assert len(headlines) == 1
        assert headlines[0]["title"] == "Test headline"
        assert "source" in headlines[0]
        assert "sentiment" in headlines[0]


# ── Integration test (mocked DB) ─────────────────────────────────────────────

class TestBuildNewsContext:
    def test_returns_empty_when_no_pool(self):
        with patch("ai_service.context.news_context.get_pg_pool", return_value=None):
            result = asyncio.run(build_news_context(symbol="BTCUSDT"))
        assert result.article_count == 0
        assert len(result.caveats) > 0

    def test_returns_context_with_articles(self):
        articles = [
            _make_article(title="BTC breaks 100k", symbols_mentioned=["BTC"]),
            _make_article(title="ETH rally continues", symbols_mentioned=["ETH"]),
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=[
            # symbol articles
            [_dict_to_record(a) for a in articles[:1]],
            # trending articles
            [_dict_to_record(a) for a in articles],
            # trending symbols
            [{"symbol": "BTC", "mention_count": 5, "avg_sentiment": 0.3}],
        ])

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=_AsyncCtxMgr(mock_conn))

        with patch("ai_service.context.news_context.get_pg_pool", return_value=mock_pool):
            result = asyncio.run(build_news_context(symbol="BTCUSDT", query="bitcoin price"))

        assert result.article_count >= 1
        assert result.symbol == "BTC"
        assert len(result.top_headlines) >= 1
        assert result.sentiment_summary["direction"] in ("bullish", "bearish", "neutral")


# ── Test helpers ──────────────────────────────────────────────────────────────

def _dict_to_record(d):
    """Create a mock asyncpg Record-like object from a dict."""
    class MockRecord(dict):
        def get(self, key, default=None):
            return super().get(key, default)
    return MockRecord(d)


class _AsyncCtxMgr:
    """Async context manager for mocking pool.acquire()."""
    def __init__(self, conn):
        self._conn = conn
    async def __aenter__(self):
        return self._conn
    async def __aexit__(self, *args):
        pass
