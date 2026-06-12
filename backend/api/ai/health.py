"""AI health endpoint."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from backend.core.auth_dependencies import get_optional_user
from backend.core.postgres import pg_health_check
from backend.models.ai.chart_actions import AIChartActionType
from backend.models.ai.common import AIHealthResponse
from ai_service.actions.registry import ACTION_CATALOG_VERSION
from ai_service.config import load_settings
from ai_service.providers.router import get_provider_router

router = APIRouter()
logger = logging.getLogger("backend.api.ai.health")


@router.get("/health", response_model=AIHealthResponse)
async def ai_health(user: dict | None = Depends(get_optional_user)):
    """Check AI status, provider availability, RAG, and action catalog."""
    pg_status = await pg_health_check()
    db_ready = pg_status.get("status") == "healthy"
    settings = load_settings()
    provider_router = get_provider_router()
    providers = provider_router.get_available_providers()
    health = await provider_router.health_check_all()
    effective_provider = "none"
    for name in provider_router.get_provider_order():
        status = health.get(name)
        if status and status.is_healthy:
            effective_provider = name
            break

    pgvector_ready = False
    source_count = 0
    if settings.rag_enabled:
        try:
            from ai_service.rag.knowledge_service import knowledge_health

            kb_health = await knowledge_health()
            pgvector_ready = kb_health.pgvector_available
            source_count = kb_health.source_count
        except Exception as exc:
            logger.warning("AI knowledge health failed: %s", exc)

    return AIHealthResponse(
        auth_required=True,
        database_ready=db_ready,
        mock_mode_available=False,
        chart_action_schema_version=ACTION_CATALOG_VERSION,
        supported_modes=["ask", "interact"],
        supported_action_types=[t.value for t in AIChartActionType],
        ai_mode=settings.mode,
        provider_mode=settings.mode,
        effective_provider=effective_provider,
        available_api_models=provider_router.get_available_api_models(),
        local_available=bool(health.get("local") and health["local"].is_healthy),
        action_catalog_version=ACTION_CATALOG_VERSION,
        rag_enabled=settings.rag_enabled,
        real_llm_enabled=effective_provider in {"local", "api"},
        available_providers=providers,
        pgvector_ready=pgvector_ready,
        knowledge_source_count=source_count,
    )
