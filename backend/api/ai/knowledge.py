"""
AI Knowledge endpoints — ingest, search, and health for the RAG knowledge base.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.auth_dependencies import get_current_user
from backend.core.config import AI_ENABLE_RAG
from backend.models.ai.knowledge import (
    KnowledgeIngestRequest,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeHealthResponse,
)

router = APIRouter()
logger = logging.getLogger("backend.api.ai.knowledge")


@router.post("/knowledge/ingest")
async def ingest_knowledge(
    body: KnowledgeIngestRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Ingest knowledge documents into the RAG knowledge base.

    Requires admin role. Ingests markdown files from the approved directory.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge ingestion requires admin privileges",
        )

    if not AI_ENABLE_RAG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RAG is not enabled (AI_ENABLE_RAG=false)",
        )

    from ai_service.rag.knowledge_service import ingest_directory, ingest_markdown_file

    if body.source_dir:
        result = await ingest_directory(body.source_dir, source_id=body.source_id)
    elif body.file_paths:
        results = []
        for fp in body.file_paths:
            r = await ingest_markdown_file(fp, source_id=body.source_id)
            results.append({"file": fp, **(r or {})})
        result = {
            "status": "completed",
            "files_processed": len(body.file_paths),
            "results": results,
        }
    else:
        # Default: ingest from approved knowledge base directory
        import os
        default_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "docs", "ai", "knowledge_base", "approved",
        )
        result = await ingest_directory(default_dir, source_id=body.source_id)

    return result


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    body: KnowledgeSearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Search the knowledge base using vector similarity."""
    if not AI_ENABLE_RAG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RAG is not enabled (AI_ENABLE_RAG=false)",
        )

    from backend.models.ai.rag import RAGRetrievalRequest
    from ai_service.rag.retrieval_service import retrieve

    retrieval_result = await retrieve(
        RAGRetrievalRequest(
            query=body.query,
            top_k=body.top_k,
            min_score=body.min_score,
            language=body.language,
            domain=body.domain,
            tags=body.tags,
        ),
        user_id=current_user["id"],
    )

    results = [
        {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "score": c.score,
            "document_title": c.document_title,
            "source_title": c.source_title,
            "heading": c.heading,
            "language": c.language,
            "domain": c.domain,
        }
        for c in retrieval_result.chunks
    ]

    return KnowledgeSearchResponse(
        results=results,
        query=body.query,
        total_results=len(results),
        search_latency_ms=retrieval_result.latency_ms,
    )


@router.get("/knowledge/sources")
async def list_knowledge_sources(
    current_user: dict = Depends(get_current_user),
):
    """List all knowledge base sources."""
    from backend.core.postgres import get_pg_pool

    pool = await get_pg_pool()
    if pool is None:
        return {"sources": []}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.*, (SELECT COUNT(*) FROM ai_knowledge_documents d WHERE d.source_id = s.id AND d.status = 'active') AS doc_count
            FROM ai_knowledge_sources s
            ORDER BY s.created_at DESC
            """
        )

    sources = [
        {
            "id": str(row["id"]),
            "source_id": row["source_id"],
            "title": row["title"],
            "domain": row["domain"],
            "language": row["language"],
            "source_type": row["source_type"],
            "review_status": row["review_status"],
            "doc_count": row.get("doc_count", 0),
        }
        for row in rows
    ]

    return {"sources": sources}


@router.get("/knowledge/health", response_model=KnowledgeHealthResponse)
async def knowledge_health_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Check knowledge base health and statistics."""
    from ai_service.rag.knowledge_service import knowledge_health
    return await knowledge_health()


@router.get("/knowledge/registry/validate")
async def validate_knowledge_registry(
    current_user: dict = Depends(get_current_user),
):
    """Validate knowledge-base registry metadata."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registry validation requires admin privileges",
        )
    from ai_service.rag.registry import load_registry, validate_registry

    errors = validate_registry(load_registry())
    return {"valid": not errors, "errors": errors}
