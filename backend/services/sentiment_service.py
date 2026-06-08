"""
Qwen/LiteLLM-powered sentiment scoring for persisted news articles.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from backend.core.postgres import get_pg_pool
from backend.models.ai.providers import LLMCompletionRequest, LLMMessage
from backend.services.ai.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)

SENTIMENT_PROMPT = """You are a cryptocurrency market sentiment analyst.
Analyze the following news item and return ONLY JSON.

Title: {title}
Content: {content}

Return:
{{
  "score": <float from -1.0 to 1.0>,
  "label": "bullish|bearish|neutral",
  "confidence": <float 0.0 to 1.0>
}}
"""


async def score_article_sentiment(title: str, content: str) -> dict:
    prompt = SENTIMENT_PROMPT.format(title=title[:300], content=(content or title)[:600])

    try:
        provider = LiteLLMProvider(provider_name="qwen_api", model_name="openai/qwen-plus")
        request = LLMCompletionRequest(
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=120,
            temperature=0.1,
        )
        response = await provider.generate_chat_completion(request)
        text = response.content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        payload = json.loads(text)
        score = max(-1.0, min(1.0, float(payload.get("score", 0.0))))
        label = payload.get("label", "neutral")
        if label not in {"bullish", "bearish", "neutral"}:
            label = "neutral"
        confidence = max(0.0, min(1.0, float(payload.get("confidence", 0.5))))
        return {"score": score, "label": label, "confidence": confidence}
    except Exception as exc:
        logger.warning("Qwen sentiment scoring failed, falling back to heuristic: %s", exc)
        lower = f"{title} {content}".lower()
        # Expanded keyword lists for better coverage
        bullish_terms = [
            "surge", "rally", "bull", "gain", "breakout", "approval", "high",
            "soar", "pump", "moon", "ATH", "break", "surpass", "upgrade",
            "adoption", "institutional", "ETF", "record", "all-time", "launch",
            "partnership", "bullish", "optimistic", "growth", "sector",
        ]
        bearish_terms = [
            "crash", "dump", "bear", "loss", "hack", "drop", "lawsuit",
            "liquidation", "plunge", "reject", "fail", "sell", "ban",
            "SEC", "investigation", "fraud", "scam", "rug", "crackdown",
            "bearish", "pessimistic", "decline", "warning", "risk", "concern",
        ]
        bull_hits = sum(1 for term in bullish_terms if term in lower)
        bear_hits = sum(1 for term in bearish_terms if term in lower)

        # Scale score based on number of matches (more matches = higher confidence)
        if bull_hits > bear_hits:
            score = min(0.5, 0.1 + bull_hits * 0.08)
            confidence = min(0.6, 0.2 + bull_hits * 0.08)
            return {"score": score, "label": "bullish", "confidence": confidence}
        if bear_hits > bull_hits:
            score = max(-0.5, -(0.1 + bear_hits * 0.08))
            confidence = min(0.6, 0.2 + bear_hits * 0.08)
            return {"score": score, "label": "bearish", "confidence": confidence}
        return {"score": 0.0, "label": "neutral", "confidence": 0.15}


async def batch_score_unscored_articles(batch_size: int = 20) -> int:
    pool = await get_pg_pool()
    if pool is None:
        return 0
    scored = 0
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, content_snippet
            FROM news_articles
            WHERE sentiment_score IS NULL
            ORDER BY published_at DESC
            LIMIT $1
            """,
            batch_size,
        )
        for row in rows:
            sentiment = await score_article_sentiment(row["title"], row.get("content_snippet") or "")
            await conn.execute(
                """
                UPDATE news_articles
                SET sentiment_score = $1,
                    sentiment_label = $2,
                    sentiment_confidence = $3,
                    sentiment_computed_at = $4
                WHERE id = $5
                """,
                sentiment["score"],
                sentiment["label"],
                sentiment["confidence"],
                datetime.now(timezone.utc),
                row["id"],
            )
            scored += 1
    logger.info("Scored %d articles", scored)
    return scored
