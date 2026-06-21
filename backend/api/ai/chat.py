"""AI Chat endpoint.

Thin authenticated REST adapter over centralized `ai_service` orchestration.
When ``AI_SERVICE_EMBEDDED=false``, the backend proxies the request to the
standalone ``ai-service`` container over HTTP.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chat import AIChatRequest, AIChatResponse
from ai_service.core.orchestrator import run_chat as _embedded_run_chat
from backend.services.ai.ai_proxy import chat as _proxy_chat

_USE_PROXY = os.getenv("AI_SERVICE_EMBEDDED", "true").lower() != "true"

if _USE_PROXY:
    run_chat = _proxy_chat
else:
    run_chat = _embedded_run_chat

router = APIRouter()


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Send a message through the unified Ask/Interact AI pipeline."""
    return await run_chat(body=body, user_id=current_user["id"], request=request)
