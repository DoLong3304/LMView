"""AI API routes for standalone service.

Mirrors ``backend/api/ai`` endpoints:
- POST /ai/chat
- GET /ai/health
- POST /ai/actions/validate
- GET /ai/actions/catalog
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chat import AIChatRequest, AIChatResponse
from backend.models.ai.chart_actions import AIChartActionValidateRequest

from ai_service.core.orchestrator import run_chat
# Placeholder imports for future routes

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


@router.get("/health")
async def health() -> dict:
    """Simple health check for AI service container.
    Returns status ok.
    """
    return {"status": "ok", "service": "ai"}

# Future: actions validation, catalog endpoints – import from ai_service.actions if needed.
