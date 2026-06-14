"""News & Sentiment Expert — gathers and structures news context.

Uses the existing news context builder and wraps FinBERT sentiment results
(when available) or falls back to the existing cached sentiment data.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai_service.agents.base_expert import BaseExpert
from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput

logger = logging.getLogger("ai_service.agents.experts.news_sentiment")


class NewsSentimentExpert(BaseExpert):
    """Gathers and structures news sentiment context."""

    name = "news_sentiment"

    async def execute(self, state: AgentState) -> ExpertOutput:
        """Assemble news context from existing services."""
        chart_context = state.get("chart_context")
        user_query = state.get("user_query", "")
        symbol = state.get("symbol")

        data_sources: List[str] = []
        warnings: List[str] = []
        structured: Dict[str, Any] = {
            "symbol": symbol,
            "articles": [],
            "sentiment_summary": {},
            "risk_events": [],
            "trending_symbols": [],
        }

        try:
            from ai_service.context.context_service import assemble_news_context
            news_ctx = await assemble_news_context(
                chart_context=chart_context,
                user_query=user_query,
            )
        except Exception as exc:
            logger.warning("News context assembly failed: %s", exc)
            return ExpertOutput(
                expert_name=self.name,
                content="News context unavailable.",
                structured_data=structured,
                confidence=0.1,
                warnings=[f"News context error: {str(exc)[:200]}"],
            )

        if not news_ctx or news_ctx.article_count == 0:
            return ExpertOutput(
                expert_name=self.name,
                content="No relevant news articles found.",
                structured_data=structured,
                confidence=0.15,
                data_sources=["news_fetcher"],
                warnings=["No news articles available for analysis."],
            )

        # Structure the news context
        data_sources.append("news_fetcher")
        structured["article_count"] = news_ctx.article_count
        structured["source_count"] = news_ctx.source_count

        if news_ctx.sentiment_summary:
            structured["sentiment_summary"] = news_ctx.sentiment_summary
            data_sources.append("vader_sentiment")

        if news_ctx.top_headlines:
            structured["articles"] = news_ctx.top_headlines[:6]

        if news_ctx.risk_events:
            structured["risk_events"] = news_ctx.risk_events[:3]

        if news_ctx.trending_symbols:
            structured["trending_symbols"] = news_ctx.trending_symbols[:5]

        if news_ctx.freshness:
            structured["freshness"] = news_ctx.freshness
            if news_ctx.freshness.get("is_stale"):
                warnings.append("News data is stale — may not reflect current events.")

        if news_ctx.caveats:
            warnings.extend(news_ctx.caveats)

        # Try FinBERT cached results if available
        finbert_data = await _try_finbert_cache(symbol)
        if finbert_data:
            structured["finbert_sentiment"] = finbert_data
            data_sources.append("finbert_cache")

        # Build content summary
        direction = structured["sentiment_summary"].get("direction", "neutral")
        content_parts = [
            f"News sentiment for {symbol or 'market'}: {direction}",
            f"Articles: {news_ctx.article_count}, Sources: {news_ctx.source_count}",
        ]
        if structured["risk_events"]:
            content_parts.append(f"⚠️ Risk events detected: {len(structured['risk_events'])}")

        confidence = min(0.8, 0.3 + news_ctx.article_count * 0.05)
        if news_ctx.freshness and news_ctx.freshness.get("is_stale"):
            confidence *= 0.7

        return ExpertOutput(
            expert_name=self.name,
            content="\n".join(content_parts),
            structured_data=structured,
            confidence=confidence,
            data_sources=data_sources,
            warnings=warnings,
        )


async def _try_finbert_cache(symbol: Optional[str]) -> Optional[Dict[str, Any]]:
    """Try to read cached FinBERT sentiment from PostgreSQL.

    Returns None if the FinBERT worker hasn't processed relevant articles
    or if the cache table doesn't exist yet.
    """
    try:
        from backend.core.postgres import get_pg_pool
        pool = get_pg_pool()
        if not pool:
            return None

        query = """
            SELECT sentiment_score, sentiment_confidence, sentiment_label,
                   detected_entities, event_category, affected_assets,
                   market_relevance, processed_at
            FROM news_sentiment_cache
            WHERE $1 = ANY(affected_assets)
            ORDER BY processed_at DESC
            LIMIT 5
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, symbol)
            if not rows:
                return None

            results = []
            for row in rows:
                results.append({
                    "score": float(row["sentiment_score"]) if row["sentiment_score"] else 0.0,
                    "confidence": float(row["sentiment_confidence"]) if row["sentiment_confidence"] else 0.0,
                    "label": row["sentiment_label"],
                    "entities": row["detected_entities"] or [],
                    "category": row["event_category"],
                    "relevance": float(row["market_relevance"]) if row["market_relevance"] else 0.0,
                })

            avg_score = sum(r["score"] for r in results) / len(results)
            return {
                "avg_score": round(avg_score, 4),
                "sample_count": len(results),
                "results": results,
            }
    except Exception as exc:
        logger.debug("FinBERT cache read failed (expected if not deployed): %s", exc)
        return None
