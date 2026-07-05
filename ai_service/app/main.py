"""LMView AI Service -- FastAPI entry point.

Standalone service that re-uses the existing ``ai_service.core`` modules.
Routes mirror the legacy backend AI endpoints so the FastAPI backend can
proxy to this service transparently.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_service.app.routes import router as ai_router
from ai_service.providers.router import get_provider_router

logger = logging.getLogger("ai_service.app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm AI providers on startup."""
    logger.info("AI service starting -- pre-warming providers...")
    try:
        router = get_provider_router()
        await router.warmup_all()
    except Exception as exc:
        logger.warning("Provider pre-warming failed (non-fatal): %s", exc)
    yield
    logger.info("AI service shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LMView AI Service",
        version="0.1.0",
        description="Standalone AI service for Ask/Interact modes.",
        lifespan=lifespan,
    )

    app.include_router(ai_router, prefix="/ai")

    @app.get("/health")
    async def root_health() -> dict:
        return {"status": "ok", "service": "ai"}

    return app


app = create_app()
