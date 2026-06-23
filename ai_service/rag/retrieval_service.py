"""
Retrieval service — top-k vector similarity search over the knowledge base.

Uses pgvector cosine similarity for nearest-neighbor retrieval.
Supports filtering by language, domain, tags, credibility level, and review status.
All retrievals are logged for audit and evaluation.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.config import AI_KB_APPROVED_ONLY, AI_RAG_MIN_SCORE, AI_RAG_TOP_K
from backend.core.postgres import get_pg_pool
from backend.models.ai.rag import (
    RAGChunkResult,
    RAGRetrievalRequest,
    RAGRetrievalResponse,
    RAGRetrievalWarning,
)
from backend.services.ai import metrics as ai_metrics
from ai_service.rag.knowledge_service import compute_embedding

logger = logging.getLogger("ai_service.rag.retrieval_service")


async def retrieve(
    request: RAGRetrievalRequest,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    message_id: Optional[str] = None,
) -> RAGRetrievalResponse:
    """
    Perform top-k retrieval from the knowledge base.

    Steps:
    1. Compute query embedding.
    2. Build filtered SQL query with pgvector cosine similarity.
    3. Return ranked chunks with metadata.
    4. Log the retrieval for audit.

    Args:
        request: Retrieval parameters (query, top_k, filters).
        user_id: Optional user ID for audit logging.
        session_id: Optional session ID for audit logging.
        message_id: Optional message ID for audit logging.

    Returns:
        RAGRetrievalResponse with ranked chunks and warnings.
    """
    start_ms = time.monotonic_ns() // 1_000_000
    warnings: List[RAGRetrievalWarning] = []

    pool = await get_pg_pool()
    if pool is None:
        return RAGRetrievalResponse(
            query=request.query,
            warnings=[RAGRetrievalWarning(
                code="db_unavailable",
                message="Database unavailable for retrieval",
                severity="error",
            )],
        )

    # Compute query embedding
    emb_start = time.monotonic()
    query_embedding = compute_embedding(request.query)
    emb_duration = time.monotonic() - emb_start
    if query_embedding is None:
        ai_metrics.record_embedding(model="unknown", duration_sec=emb_duration, success=False)
        # Fallback to BM25-only search
        from ai_service.rag.bm25_search import bm25_search
        bm25_hits = await bm25_search(request.query, top_k=request.top_k or AI_RAG_TOP_K, language=request.language)
        chunks = []
        async with pool.acquire() as conn:
            for cid_uuid, score in bm25_hits:
                row = await conn.fetchrow(
                    """
                    SELECT c.id AS chunk_id, c.content AS chunk_text,
                           c.heading, c.language AS chunk_language,
                           c.document_id, d.title AS doc_title,
                           d.domain AS doc_domain, d.tags AS doc_tags,
                           s.credibility_level,
                           s.id AS source_uuid, s.title AS source_title
                    FROM ai_knowledge_chunks c
                    JOIN ai_knowledge_documents d ON d.id = c.document_id
                    LEFT JOIN ai_knowledge_sources s ON s.id = d.source_id
                    WHERE c.id = $1
                    """,
                    cid_uuid,
                )
                if row is None:
                    continue
                chunks.append(RAGChunkResult(
                    chunk_id=str(row["chunk_id"]),
                    text=row["chunk_text"] or "",
                    score=round(min(score * 100, 1.0), 4),
                    document_id=str(row["document_id"]),
                    document_title=row.get("doc_title", "") or "",
                    source_id=str(row["source_uuid"]) if row.get("source_uuid") else None,
                    source_title=row.get("source_title"),
                    heading=row.get("heading"),
                    language=row.get("chunk_language"),
                    domain=row.get("doc_domain"),
                    tags=json.loads(row["doc_tags"]) if row.get("doc_tags") else [],
                    credibility_level=row.get("credibility_level"),
                    citation={
                        "document_title": row.get("doc_title", "") or "",
                        "source_title": row.get("source_title"),
                        "heading": row.get("heading"),
                    },
                ))
        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        return RAGRetrievalResponse(
            query=request.query,
            chunks=chunks,
            total_results=len(chunks),
            latency_ms=elapsed_ms,
            warnings=[RAGRetrievalWarning(
                code="embedding_unavailable",
                message="Embedding model unavailable — used BM25 keyword search",
                severity="warning",
            )],
        )
    ai_metrics.record_embedding(model="default", duration_sec=emb_duration, success=True)

    top_k = request.top_k or AI_RAG_TOP_K
    min_score = request.min_score if request.min_score is not None else AI_RAG_MIN_SCORE

    # Build query with filters
    embedding_str = str(query_embedding)
    query_sql, params = _build_retrieval_query(
        embedding_str=embedding_str,
        top_k=top_k,
        min_score=min_score,
        language=request.language,
        domain=request.domain,
        tags=request.tags,
        source_type=request.source_type,
        credibility_level=request.credibility_level,
        review_status=request.review_status,
        symbol=request.symbol,
        exchange=request.exchange,
        timeframe=request.timeframe,
        use_hybrid_search=request.use_hybrid_search,
        query_text=request.query,
    )

    # Mark the start of the vector-search phase so we can split the
    # retrieval latency into ``embedding`` and ``vector_search`` (B13
    # observability — see docs/dataflow_analysis_and_observability_plan.md
    # §3.7 and Phần B.7).
    vs_start = time.monotonic()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query_sql, *params)
    except Exception as exc:
        vs_duration = time.monotonic() - vs_start
        ai_metrics.record_rag_vector_search(duration_sec=vs_duration, success=False)
        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        logger.error("Retrieval failed: %s", exc)
        return RAGRetrievalResponse(
            query=request.query,
            latency_ms=elapsed_ms,
            warnings=[RAGRetrievalWarning(
                code="retrieval_error",
                message=f"Retrieval error: {str(exc)[:200]}",
                severity="error",
            )],
        )

    vs_duration = time.monotonic() - vs_start
    ai_metrics.record_rag_vector_search(duration_sec=vs_duration, success=True)

    chunks: List[RAGChunkResult] = []

    # --- Batch 6: BM25 + RRF + reranker integration ---
    if request.use_hybrid_search and rows:
        from ai_service.rag.bm25_search import bm25_search
        from ai_service.rag.reranker import rerank

        # BM25 search
        bm25_hits = await bm25_search(request.query, top_k=top_k, language=request.language)
        bm25_map = {int(cid): rank for rank, (cid, _score) in enumerate(bm25_hits, start=1)}

        # Vector hits with rank
        vector_map = {}
        for idx, row in enumerate(rows, start=1):
            vector_map[int(row["chunk_id"])] = idx

        all_cids = set(bm25_map.keys()) | set(vector_map.keys())
        rrf_candidates = []
        for cid in all_cids:
            r_b = bm25_map.get(cid, 0)
            r_v = vector_map.get(cid, 0)
            rrf_score = 0.0
            if r_b:
                rrf_score += 1.0 / (60 + r_b)
            if r_v:
                rrf_score += 1.0 / (60 + r_v)
            rrf_candidates.append((cid, rrf_score))
        rrf_candidates.sort(key=lambda x: x[1], reverse=True)
        rrf_candidates = rrf_candidates[:top_k]

        # Load chunk texts for reranker
        candidate_texts = []
        for cid, _score in rrf_candidates:
            for row in rows:
                if int(row["chunk_id"]) == cid:
                    candidate_texts.append((cid, row["chunk_text"]))
                    break

        # Rerank
        reranked = await rerank(request.query, candidate_texts)
        reranked = reranked[:top_k]

        # Build results from reranked list
        id_to_row = {int(row["chunk_id"]): row for row in rows}
        for cid, _score in reranked:
            row = id_to_row.get(cid)
            if row is None:
                continue
            score = 1.0 - float(row.get("distance", 1.0))
            if score < min_score:
                continue
            chunks.append(RAGChunkResult(
                chunk_id=str(row["chunk_id"]),
                text=row["chunk_text"],
                score=round(score, 4),
                document_id=str(row["document_id"]),
                document_title=row.get("doc_title", ""),
                source_id=str(row["source_uuid"]) if row.get("source_uuid") else None,
                source_title=row.get("source_title"),
                heading=row.get("heading"),
                language=row.get("chunk_language"),
                domain=row.get("doc_domain"),
                tags=json.loads(row["doc_tags"]) if row.get("doc_tags") else [],
                credibility_level=row.get("credibility_level"),
                citation={
                    "document_title": row.get("doc_title", ""),
                    "source_title": row.get("source_title"),
                    "heading": row.get("heading"),
                    "chunk_index": row.get("chunk_index"),
                },
            ))
    else:
        # Pure vector search (existing behavior)
        for row in rows:
            score = 1.0 - (row.get("distance", 1.0))
            if score < min_score:
                continue
            chunks.append(RAGChunkResult(
                chunk_id=str(row["chunk_id"]),
                text=row["chunk_text"],
                score=round(score, 4),
                document_id=str(row["document_id"]),
                document_title=row.get("doc_title", ""),
                source_id=str(row["source_uuid"]) if row.get("source_uuid") else None,
                source_title=row.get("source_title"),
                heading=row.get("heading"),
                language=row.get("chunk_language"),
                domain=row.get("doc_domain"),
                tags=json.loads(row["doc_tags"]) if row.get("doc_tags") else [],
                credibility_level=row.get("credibility_level"),
                citation={
                    "document_title": row.get("doc_title", ""),
                    "source_title": row.get("source_title"),
                    "heading": row.get("heading"),
                    "chunk_index": row.get("chunk_index"),
                },
            ))

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    # RAG retrieval outcome (B13 metrics) — observe latency, top-k,
    # relevance score, and zero-result rate.
    ai_metrics.record_rag_retrieval(
        duration_sec=elapsed_ms / 1000.0,
        n_results=len(chunks),
        top_score=sum(c.score for c in chunks) / len(chunks) if chunks else 0.0,
        cache_hit=False,
    )

    # Add warnings for weak results
    if not chunks:
        warnings.append(RAGRetrievalWarning(
            code="no_results",
            message="No relevant knowledge base entries found for your query",
            severity="warning",
        ))
    elif len(chunks) < 3:
        warnings.append(RAGRetrievalWarning(
            code="few_results",
            message=f"Only {len(chunks)} relevant entries found — response may be less comprehensive",
            severity="info",
        ))

    # Log the retrieval
    await _log_retrieval(
        pool=pool,
        user_id=user_id,
        session_id=session_id,
        message_id=message_id,
        query_text=request.query,
        query_embedding=embedding_str,
        top_k=top_k,
        min_score=min_score,
        filters={
            "language": request.language,
            "domain": request.domain,
            "tags": request.tags,
            "source_type": request.source_type,
        },
        result_count=len(chunks),
        result_chunk_ids=[c.chunk_id for c in chunks],
        result_scores=[c.score for c in chunks],
        latency_ms=elapsed_ms,
    )

    return RAGRetrievalResponse(
        chunks=chunks,
        query=request.query,
        total_results=len(chunks),
        top_k_used=top_k,
        min_score_used=min_score,
        latency_ms=elapsed_ms,
        warnings=warnings,
    )


def _build_retrieval_query(
    embedding_str: str,
    top_k: int,
    min_score: float,
    language: Optional[str] = None,
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source_type: Optional[str] = None,
    credibility_level: Optional[str] = None,
    review_status: Optional[str] = None,
    symbol: Optional[str] = None,
    exchange: Optional[str] = None,
    timeframe: Optional[str] = None,
    use_hybrid_search: bool = False,
    query_text: Optional[str] = None,
) -> tuple:
    """Build the pgvector similarity search SQL query with filters.

    Supports:
    - Vector cosine similarity (default)
    - Hybrid search (vector + keyword via ``query_text``)
    - Metadata filtering by symbol, exchange, timeframe, tags
    """
    # cosine distance: 1 - similarity
    max_distance = 1.0 - min_score

    # Determine the ORDER BY and score expressions based on search mode
    if use_hybrid_search and query_text:
        # Hybrid: combine vector similarity with keyword ts_rank
        # Use ts_query for keyword matching on chunk content
        select_expr = """
            e.chunk_id,
            c.content AS chunk_text,
            c.heading,
            c.chunk_index,
            c.language AS chunk_language,
            e.document_id,
            d.title AS doc_title,
            d.domain AS doc_domain,
            d.tags AS doc_tags,
            s.id AS source_uuid,
            s.title AS source_title,
            s.credibility_level,
            -- Hybrid score: 60% vector + 40% keyword
            (0.6 * (1.0 - (e.embedding <=> $1::vector)) +
             0.4 * COALESCE(
                ts_rank_cd(
                    c.content_tsv,
                    plainto_tsquery('english', $2::text)
                ), 0.0)
            ) AS hybrid_score
        """
        order_expr = "ORDER BY hybrid_score DESC"
        score_filter = f"AND (1.0 - (e.embedding <=> $1::vector)) >= {max_distance}"
        params: List[Any] = [embedding_str, query_text]
        param_idx = 3
    else:
        # Pure vector search (default)
        select_expr = """
            e.chunk_id,
            c.content AS chunk_text,
            c.heading,
            c.chunk_index,
            c.language AS chunk_language,
            e.document_id,
            d.title AS doc_title,
            d.domain AS doc_domain,
            d.tags AS doc_tags,
            s.id AS source_uuid,
            s.title AS source_title,
            s.credibility_level,
            e.embedding <=> $1::vector AS distance
        """
        order_expr = f"ORDER BY distance ASC LIMIT ${param_idx + 6}"
        score_filter = f"AND e.embedding <=> $1::vector < ${param_idx}"
        params: List[Any] = [embedding_str]
        param_idx = 2

    # Build score filter and placeholder for hybrid vs vector
    sql_parts = [
        """
        SELECT
        """,
        select_expr,
        """
        FROM ai_knowledge_embeddings e
        JOIN ai_knowledge_chunks c ON c.id = e.chunk_id
        JOIN ai_knowledge_documents d ON d.id = e.document_id
        LEFT JOIN ai_knowledge_sources s ON s.id = c.source_id
        WHERE d.status = 'active'
        """,
    ]

    # Apply filters
    if AI_KB_APPROVED_ONLY or review_status == "approved":
        sql_parts.append("AND s.review_status = 'approved'")
        sql_parts.append("AND s.allowed_for_rag = TRUE")

    if language:
        sql_parts.append(f"AND c.language = ${param_idx}")
        params.append(language)
        param_idx += 1

    if domain:
        sql_parts.append(f"AND d.domain = ${param_idx}")
        params.append(domain)
        param_idx += 1

    if source_type:
        sql_parts.append(f"AND d.source_type = ${param_idx}")
        params.append(source_type)
        param_idx += 1

    if credibility_level:
        sql_parts.append(f"AND s.credibility_level = ${param_idx}")
        params.append(credibility_level)
        param_idx += 1

    # Metadata filtering by symbol/exchange/timeframe
    if symbol:
        sql_parts.append(f"AND (d.tags @> ${param_idx}::jsonb OR c.content ILIKE '%' || ${param_idx + 1}::text || '%')")
        params.append(json.dumps([symbol]))
        params.append(symbol)
        param_idx += 2

    if exchange:
        sql_parts.append(f"AND (d.tags @> ${param_idx}::jsonb OR c.content ILIKE '%' || ${param_idx + 1}::text || '%')")
        params.append(json.dumps([exchange]))
        params.append(exchange)
        param_idx += 2

    if timeframe:
        sql_parts.append(f"AND d.tags @> ${param_idx}::jsonb")
        params.append(json.dumps([timeframe]))
        param_idx += 1

    # Tag filtering with AND logic for multiple tags
    if tags and len(tags) > 0:
        for tag in tags:
            sql_parts.append(f"AND d.tags @> ${param_idx}::jsonb")
            params.append(json.dumps([tag]))
            param_idx += 1

    if use_hybrid_search and query_text:
        # Keyword filter for hybrid
        sql_parts.append(f"AND c.content_tsv @@ plainto_tsquery('english', $2::text)")
        # Already applied score_filter above
    else:
        # Vector distance filter
        sql_parts.append(score_filter)
        params.append(max_distance)
        param_idx += 1

        sql_parts.append(order_expr)
        params.append(top_k)

    return "\n".join(sql_parts), params


async def _log_retrieval(
    pool,
    user_id: Optional[str],
    session_id: Optional[str],
    message_id: Optional[str],
    query_text: str,
    query_embedding: str,
    top_k: int,
    min_score: float,
    filters: dict,
    result_count: int,
    result_chunk_ids: List[str],
    result_scores: List[float],
    latency_ms: int,
) -> None:
    """Log a retrieval query for audit."""
    try:
        import uuid as uuid_mod
        uid = uuid_mod.UUID(user_id) if user_id else None
        sid = uuid_mod.UUID(session_id) if session_id else None
        mid = uuid_mod.UUID(message_id) if message_id else None

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ai_knowledge_retrieval_logs (
                    user_id, session_id, message_id, query_text,
                    top_k, min_score, filters,
                    result_count, result_chunk_ids, result_scores,
                    latency_ms, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9::jsonb, $10::jsonb, $11, $12)
                """,
                uid, sid, mid, query_text[:2000],
                top_k, min_score, json.dumps(filters),
                result_count, json.dumps(result_chunk_ids), json.dumps(result_scores),
                latency_ms, datetime.now(timezone.utc),
            )
    except Exception as exc:
        logger.warning("Failed to log retrieval: %s", exc)
