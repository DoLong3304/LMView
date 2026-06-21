"""LMView AI Service – FastAPI entry point.

Standalone service that re-uses the existing ``ai_service.core`` modules.
Routes mirror the legacy backend AI endpoints so the FastAPI backend can
proxy to this service transparently.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from ai_service.app.routes import router as ai_router

logger = logging.getLogger("ai_service.app.main")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LMView AI Service",
        version="0.1.0",
        description="Standalone AI service for Ask/Interact modes.",
    )

    app.include_router(ai_router, prefix="/ai")

    @app.get("/health")
    async def root_health() -> dict:
        return {"status": "ok", "service": "ai"}

    return app


app = create_app()
