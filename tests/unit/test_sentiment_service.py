"""Unit tests for backend.services.sentiment_service.

Tests cover:
- Qwen LLM scoring (mocked provider)
- Heuristic fallback scoring with keyword lists
- Edge cases: empty content, garbage JSON, invalid labels
- batch_score_unscored_articles with mocked PostgreSQL pool
"""
import sys
import types
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _AsyncCtxMgr:
    """Helper: wraps an object so it works as `async with pool.acquire() as conn`."""
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def mock_pool():
    """Return a mock pool that supports `async with pool.acquire() as conn`."""
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = _AsyncCtxMgr(conn)
    pool.acquire = MagicMock(return_value=_AsyncCtxMgr(conn))
    return pool, conn


@pytest.fixture
def mock_litellm_provider():
    """Return a mock LiteLLMProvider that returns valid JSON."""
    provider = AsyncMock()
    response = MagicMock()
    response.content = json.dumps({"score": 0.7, "label": "bullish", "confidence": 0.85})
    provider.generate_chat_completion = AsyncMock(return_value=response)
    return provider


# ---------------------------------------------------------------------------
# Tests: score_article_sentiment — LLM path
# ---------------------------------------------------------------------------

class TestScoreArticleSentimentLLM:
    """Test LLM-based sentiment scoring."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_returns_valid_bullish(self, mock_litellm_provider):
        from backend.services.sentiment_service import score_article_sentiment
        with patch("backend.services.sentiment_service.LiteLLMProvider", return_value=mock_litellm_provider):
            result = await score_article_sentiment("Bitcoin surges past $100k", "BTC rallies to new all-time high")

        assert result["label"] == "bullish"
        assert result["score"] == pytest.approx(0.7, abs=0.01)
        assert result["confidence"] == pytest.approx(0.85, abs=0.01)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_returns_bearish(self, mock_litellm_provider):
        from backend.services.sentiment_service import score_article_sentiment
        response = MagicMock()
        response.content = json.dumps({"score": -0.6, "label": "bearish", "confidence": 0.9})
        mock_litellm_provider.generate_chat_completion = AsyncMock(return_value=response)

        with patch("backend.services.sentiment_service.LiteLLMProvider", return_value=mock_litellm_provider):
            result = await score_article_sentiment("Market crashes", "Bitcoin drops 20%")

        assert result["label"] == "bearish"
        assert result["score"] == pytest.approx(-0.6, abs=0.01)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_returns_neutral(self, mock_litellm_provider):
        from backend.services.sentiment_service import score_article_sentiment
        response = MagicMock()
        response.content = json.dumps({"score": 0.0, "label": "neutral", "confidence": 0.3})
        mock_litellm_provider.generate_chat_completion = AsyncMock(return_value=response)

        with patch("backend.services.sentiment_service.LiteLLMProvider", return_value=mock_litellm_provider):
            result = await score_article_sentiment("Trading volume stable", "No significant change")

        assert result["label"] == "neutral"
        assert result["score"] == pytest.approx(0.0, abs=0.01)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_score_clamped_to_range(self, mock_litellm_provider):
        """Score must be clamped to [-1.0, 1.0] even if LLM returns outside range."""
        from backend.services.sentiment_service import score_article_sentiment
        response = MagicMock()
        response.content = json.dumps({"score": 5.0, "label": "bullish", "confidence": 2.0})
        mock_litellm_provider.generate_chat_completion = AsyncMock(return_value=response)

        with patch("backend.services.sentiment_service.LiteLLMProvider", return_value=mock_litellm_provider):
            result = await score_article_sentiment("Moon", "To the moon")

        assert result["score"] == 1.0
        assert result["confidence"] == 1.0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_invalid_label_falls_to_neutral(self, mock_litellm_provider):
        from backend.services.sentiment_service import score_article_sentiment
        response = MagicMock()
        response.content = json.dumps({"score": 0.5, "label": "super_bullish", "confidence": 0.7})
        mock_litellm_provider.generate_chat_completion = AsyncMock(return_value=response)

        with patch("backend.services.sentiment_service.LiteLLMProvider", return_value=mock_litellm_provider):
            result = await score_article_sentiment("Test", "Content")

        assert result["label"] == "neutral"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_json_with_markdown_fences(self, mock_litellm_provider):
        """LLM may wrap JSON in ```json...``` blocks."""
        from backend.services.sentiment_service import score_article_sentiment
        response = MagicMock()
        response.content = '```json\n{"score": 0.4, "label": "bullish", "confidence": 0.6}\n```'
        mock_litellm_provider.generate_chat_completion = AsyncMock(return_value=response)

        with patch("backend.services.sentiment_service.LiteLLMProvider", return_value=mock_litellm_provider):
            result = await score_article_sentiment("Test", "Content")

        assert result["label"] == "bullish"
        assert result["score"] == pytest.approx(0.4, abs=0.01)


# ---------------------------------------------------------------------------
# Tests: score_article_sentiment — heuristic fallback path
# ---------------------------------------------------------------------------

class TestScoreArticleSentimentHeuristic:
    """Test heuristic fallback when LLM fails."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_bullish_keywords(self):
        from backend.services.sentiment_service import score_article_sentiment
        with patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("LLM unavailable")):
            result = await score_article_sentiment("Bitcoin surges past resistance, ETF approval rally", "")

        assert result["label"] == "bullish"
        assert result["score"] > 0
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_bearish_keywords(self):
        from backend.services.sentiment_service import score_article_sentiment
        with patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("LLM unavailable")):
            result = await score_article_sentiment("Market crash, SEC investigation, hack and dump", "")

        assert result["label"] == "bearish"
        assert result["score"] < 0
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_neutral_when_no_keywords(self):
        from backend.services.sentiment_service import score_article_sentiment
        with patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("LLM unavailable")):
            result = await score_article_sentiment("Blockchain technology update released", "Version 2.1.0")

        assert result["label"] == "neutral"
        assert result["score"] == 0.0
        assert result["confidence"] == pytest.approx(0.15, abs=0.01)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_more_keywords_higher_magnitude(self):
        from backend.services.sentiment_service import score_article_sentiment
        with patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("LLM unavailable")):
            low = await score_article_sentiment("Bitcoin rally today", "")
        with patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("LLM unavailable")):
            high = await score_article_sentiment("Bitcoin rally surge breakout pump bull ETF approval record", "")

        assert high["score"] > low["score"]
        assert high["confidence"] > low["confidence"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_mixed_keywords_neutral(self):
        """When equal bull/bear keywords, result is neutral."""
        from backend.services.sentiment_service import score_article_sentiment
        with patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("LLM unavailable")):
            result = await score_article_sentiment("rally crash", "surge dump")

        assert result["label"] == "neutral"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_empty_title_and_content(self):
        from backend.services.sentiment_service import score_article_sentiment
        with patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("LLM unavailable")):
            result = await score_article_sentiment("", "")

        assert result["label"] == "neutral"
        assert result["score"] == 0.0


# ---------------------------------------------------------------------------
# Tests: batch_score_unscored_articles
# ---------------------------------------------------------------------------

class TestBatchScoreUnscoredArticles:
    """Test batch scoring of unscored articles from PostgreSQL."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scores_unscored_articles(self, mock_pool):
        from backend.services.sentiment_service import batch_score_unscored_articles
        pool, conn = mock_pool

        # Simulate 3 unscored rows
        rows = [
            {"id": 1, "title": "Bitcoin rally", "content_snippet": "BTC surges"},
            {"id": 2, "title": "Market crash", "content_snippet": "Prices drop"},
            {"id": 3, "title": "Neutral news", "content_snippet": "Nothing happened"},
        ]
        conn.fetch = AsyncMock(return_value=rows)
        conn.execute = AsyncMock(return_value="UPDATE 1")

        with patch("backend.services.sentiment_service.get_pg_pool", return_value=pool), \
             patch("backend.services.sentiment_service.LiteLLMProvider", side_effect=Exception("No LLM")):
            scored = await batch_score_unscored_articles(batch_size=10)

        assert scored == 3
        assert conn.fetch.call_count == 1
        assert conn.execute.call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_unscored_articles(self, mock_pool):
        from backend.services.sentiment_service import batch_score_unscored_articles
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[])

        with patch("backend.services.sentiment_service.get_pg_pool", return_value=pool):
            scored = await batch_score_unscored_articles(batch_size=10)

        assert scored == 0
        assert conn.execute.call_count == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pool_unavailable_returns_zero(self):
        from backend.services.sentiment_service import batch_score_unscored_articles
        with patch("backend.services.sentiment_service.get_pg_pool", return_value=None):
            scored = await batch_score_unscored_articles(batch_size=10)

        assert scored == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_size_limit(self, mock_pool):
        from backend.services.sentiment_service import batch_score_unscored_articles
        pool, conn = mock_pool
        conn.fetch = AsyncMock(return_value=[])
        conn.execute = AsyncMock(return_value="UPDATE 1")

        with patch("backend.services.sentiment_service.get_pg_pool", return_value=pool):
            await batch_score_unscored_articles(batch_size=5)

        # Verify LIMIT parameter passed
        call_args = conn.fetch.call_args
        assert call_args[0][-1] == 5  # last arg is batch_size LIMIT
