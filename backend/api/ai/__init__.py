"""
AI API package — modular route handlers for AI endpoints.

Re-exports the combined router for backward compatibility with app.py.
"""
from fastapi import APIRouter

from backend.api.ai.chat import router as chat_router
from backend.api.ai.sessions import router as sessions_router
from backend.api.ai.chart_context import router as chart_context_router
from backend.api.ai.chart_actions import router as chart_actions_router
from backend.api.ai.actions import router as actions_router
from backend.api.ai.health import router as health_router
from backend.api.ai.knowledge import router as knowledge_router
from backend.api.ai.tours import router as tours_router

router = APIRouter(prefix="/api/ai", tags=["ai"])

router.include_router(health_router)
router.include_router(chat_router)
router.include_router(sessions_router)
router.include_router(chart_context_router)
router.include_router(chart_actions_router)
router.include_router(actions_router)
router.include_router(knowledge_router)
router.include_router(tours_router)
