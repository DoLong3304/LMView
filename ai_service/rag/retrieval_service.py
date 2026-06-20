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
        return RAGRetrievalResponse(
            query=request.query,
            warnings=[RAGRetrievalWarning(
                code="embedding_unavailable",
                message="Embedding model unavailable — cannot perform vector search",
                severity="error",
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
    for row in rows:
        score = 1.0 - (row.get("distance", 1.0))  # cosine distance → similarity
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
) -> tuple:
    """Build the pgvector similarity search SQL query with filters."""
    # cosine distance: 1 - similarity
    max_distance = 1.0 - min_score

    sql_parts = [
        """
        SELECT
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
        FROM ai_knowledge_embeddings e
        JOIN ai_knowledge_chunks c ON c.id = e.chunk_id
        JOIN ai_knowledge_documents d ON d.id = e.document_id
        LEFT JOIN ai_knowledge_sources s ON s.id = c.source_id
        WHERE d.status = 'active'
        """
    ]
    params: List[Any] = [embedding_str]
    param_idx = 2

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

    sql_parts.append(f"AND e.embedding <=> $1::vector < ${param_idx}")
    params.append(max_distance)
    param_idx += 1

    sql_parts.append(f"ORDER BY distance ASC LIMIT ${param_idx}")
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
