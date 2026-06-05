"""
AI Health endpoint — enhanced for Phase 1 with provider and RAG status.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends

from backend.core.auth_dependencies import get_optional_user
from backend.core.config import AI_ENABLE_RAG, AI_ENABLE_REAL_LLM, AI_MODE
from backend.core.postgres import pg_health_check
from backend.models.ai.common import AIHealthResponse
from backend.models.ai.chart_actions import AIChartActionType

router = APIRouter()
logger = logging.getLogger("backend.api.ai.health")


@router.get("/health", response_model=AIHealthResponse)
async def ai_health(user: dict | None = Depends(get_optional_user)):
    """Check AI service status including provider and RAG availability."""
    pg_status = await pg_health_check()
    db_ready = pg_status.get("status") == "healthy"

    # Check providers
    available_providers = ["mock"]
    try:
        from backend.services.ai.provider_router import get_provider_router
        router_instance = get_provider_router()
        available_providers = router_instance.get_available_providers()
    except Exception:
        pass

    # Check pgvector/RAG
    pgvector_ready = False
    source_count = 0
    if AI_ENABLE_RAG:
        try:
            from backend.services.ai.knowledge_service import knowledge_health
            kb_health = await knowledge_health()
            pgvector_ready = kb_health.pgvector_available
            source_count = kb_health.source_count
        except Exception:
            pass

    return AIHealthResponse(
        auth_required=True,
        database_ready=db_ready,
        mock_mode_available=True,
        chart_action_schema_version="1.1.0",
        supported_modes=["ask", "interact"],
        supported_action_types=[t.value for t in AIChartActionType],
        ai_mode=AI_MODE,
        rag_enabled=AI_ENABLE_RAG,
        real_llm_enabled=AI_ENABLE_REAL_LLM,
        available_providers=available_providers,
        pgvector_ready=pgvector_ready,
        knowledge_source_count=source_count,
    )
