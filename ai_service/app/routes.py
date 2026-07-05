"""AI API routes for standalone service.

Mirrors ``backend/api/ai`` endpoints:
- POST /ai/chat
- POST /ai/chat/stream (SSE streaming)
- GET /ai/health
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chat import AIChatRequest, AIChatResponse

from ai_service.core.orchestrator import run_chat
from ai_service.core.orchestrator import run_chat_stream
from ai_service.rag.auto_ingest import reindex_all_embeddings

logger = logging.getLogger("ai_service.app.routes")
router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Proxy to ``ai_service.core.orchestrator.run_chat``.
    Returns same response shape as legacy endpoint.
    """
    return await run_chat(body=body, user_id=current_user["id"])


@router.post("/chat/stream")
async def ai_chat_stream(
    body: AIChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stream AI response token-by-token via SSE."""
    async def event_generator():
        async for event in run_chat_stream(body=body, user_id=current_user["id"]):
            yield f"data: {event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/knowledge/reindex")
async def reindex_embeddings(
    current_user: dict = Depends(get_current_user),
):
    """Recompute all chunk embeddings using current embedding model.

    Run after an embedding model upgrade to refresh the vector index.
    May take 1-2 minutes depending on KB size.
    """
    result = await reindex_all_embeddings()
    logger.info("Reindex complete: %s", result)
    return result


@router.get("/health")
async def health() -> dict:
    """Health check with pipeline stats."""
    from ai_service.agents.graph import get_node_stats, get_timeout_stats
    from ai_service.core.cache import cache_stats
    return {
        "status": "ok",
        "service": "ai",
        "nodes": get_node_stats(),
        "timeouts": get_timeout_stats(),
        "cache": cache_stats(),
    }
