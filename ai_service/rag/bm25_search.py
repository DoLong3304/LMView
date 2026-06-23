"""BM25 keyword search for RAG using PostgreSQL full-text.

Implements a simple BM25-like ranking via `ts_rank_cd`.
Used as the keyword component in hybrid retrieval.
"""
from __future__ import annotations

import logging
from typing import List, Tuple, Optional

from backend.core.postgres import get_pg_pool

logger = logging.getLogger("ai_service.rag.bm25_search")

async def bm25_search(query: str, top_k: int = 10, language: Optional[str] = None) -> List[Tuple[int, float]]:
    """Perform BM25 search on `ai_knowledge_chunks`.

    Returns list of `(chunk_id, score)` sorted by descending score.
    """
    pool = await get_pg_pool()
    if pool is None:
        logger.error("Database unavailable for BM25 search")
        return []
    # Build ts_query with simple plainto_tsquery
    ts_query = f"plainto_tsquery('english', $1)"
    sql = f"""
        SELECT c.id as chunk_id,
               ts_rank_cd(c.content_tsv, {ts_query}) AS rank
        FROM ai_knowledge_chunks c
        JOIN ai_knowledge_documents d ON d.id = c.document_id
        WHERE d.status = 'active'
          AND c.content_tsv IS NOT NULL
        ORDER BY rank DESC
        LIMIT $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, query, top_k)
        return [(row["chunk_id"], float(row["rank"])) for row in rows]
