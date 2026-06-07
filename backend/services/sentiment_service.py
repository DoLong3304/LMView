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
        bullish_terms = ["surge", "rally", "bull", "gain", "breakout", "approval", "high"]
        bearish_terms = ["crash", "dump", "bear", "loss", "hack", "drop", "lawsuit", "liquidation"]
        bull_hits = sum(term in lower for term in bullish_terms)
        bear_hits = sum(term in lower for term in bearish_terms)
        if bull_hits > bear_hits:
            return {"score": 0.35, "label": "bullish", "confidence": 0.35}
        if bear_hits > bull_hits:
            return {"score": -0.35, "label": "bearish", "confidence": 0.35}
        return {"score": 0.0, "label": "neutral", "confidence": 0.1}


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
