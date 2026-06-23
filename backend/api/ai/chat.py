"""AI Chat endpoint.

Thin authenticated REST adapter over centralized `ai_service` orchestration.
When ``AI_SERVICE_EMBEDDED=false``, the backend proxies the request to the
standalone ``ai-service`` container over HTTP.

Streaming endpoint at ``POST /api/ai/chat/stream`` yields SSE token events.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chat import AIChatRequest, AIChatResponse
from backend.services.ai.ai_proxy import chat as run_chat
from backend.services.ai.ai_proxy import chat_stream as run_chat_stream
from backend.core.postgres import get_pg_pool
from datetime import datetime, timezone

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Send a message through the unified Ask/Interact AI pipeline."""
    return await run_chat(body=body, user_id=current_user["id"], request=request)


@router.post("/chat/stream")
async def ai_chat_stream(
    body: AIChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Stream AI response token-by-token via SSE."""
    async def event_generator():
        async for event in run_chat_stream(body=body, user_id=current_user["id"], request=request):
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


@router.patch("/messages/{message_id}/rate")
async def ai_rate_message(
    message_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Rate an AI assistant message (👍/👎)."""
    rating = body.get("rating")
    if rating not in (1, -1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be 1 (thumbs up) or -1 (thumbs down)")
    pool = await get_pg_pool()
    if pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE ai_chat_messages SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{user_rating}', $1::jsonb, true) WHERE id = $2::uuid AND user_id = $3 RETURNING id",
            str(rating),
            message_id,
            current_user["id"],
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return {"status": "ok", "rating": rating}
