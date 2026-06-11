"""AI Chat endpoint.

Thin authenticated REST adapter over centralized `ai_service` orchestration.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chat import AIChatRequest, AIChatResponse
from ai_service.core.orchestrator import run_chat

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send a message through the unified Ask/Interact AI pipeline."""
    return await run_chat(body=body, user_id=current_user["id"])
