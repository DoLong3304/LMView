"""AI API routes for standalone service.

Mirrors ``backend/api/ai`` endpoints:
- POST /ai/chat
- POST /ai/chat/stream (SSE streaming)
- GET /ai/health
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chat import AIChatRequest, AIChatResponse

from ai_service.core.orchestrator import run_chat
from ai_service.core.orchestrator import run_chat_stream

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


@router.get("/health")
async def health() -> dict:
    """Simple health check for AI service container.
    Returns status ok.
    """
    return {"status": "ok", "service": "ai"}
