"""Cross-encoder reranker for RAG.

Uses a lightweight sentence-transformers cross-encoder model to re-rank a list of candidate chunks
against the query. Returns the same list sorted by descending relevance score.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from backend.core.config import AI_RERANKER_MODEL

logger = logging.getLogger("ai_service.rag.reranker")

# Lazy-loaded cross-encoder model
_cross_encoder = None

def _load_cross_encoder():
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder  # type: ignore
        _cross_encoder = CrossEncoder(AI_RERANKER_MODEL)
        logger.info("Loaded cross-encoder model %s", AI_RERANKER_MODEL)
        return _cross_encoder
    except Exception as exc:
        logger.error("Failed to load cross-encoder %s: %s", AI_RERANKER_MODEL, exc)
        return None

async def rerank(query: str, candidates: List[Tuple[int, str]]) -> List[Tuple[int, float]]:
    """Rerank candidates using cross-encoder.

    Args:
        query: user query string
        candidates: list of `(chunk_id, chunk_text)`
    Returns:
        List of `(chunk_id, score)` sorted descending.
    """
    model = _load_cross_encoder()
    if model is None:
        # Fallback: return original order with dummy scores
        return [(cid, 0.0) for cid, _ in candidates]
    # Prepare pairs for the model
    pairs = [(query, text) for _, text in candidates]
    scores = model.predict(pairs)  # returns list of floats
    # Zip with chunk ids and sort
    scored = [(cid, float(score)) for (cid, _), score in zip(candidates, scores)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
