"""
AI Chart Context endpoint — store chart context snapshots.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends

from backend.core.auth_dependencies import get_current_user
from backend.models.chart_context import ChartContextDTO, ChartContextResponse
from backend.services import ai_chat_service

router = APIRouter()
logger = logging.getLogger("backend.api.ai.chart_context")


@router.post("/chart-context", response_model=ChartContextResponse)
async def submit_chart_context(
    body: ChartContextDTO,
    current_user: dict = Depends(get_current_user),
):
    """Accept and store a chart context snapshot from the frontend."""
    snapshot_id = await ai_chat_service.store_chart_snapshot(
        user_id=current_user["id"],
        session_id=None,
        context=body.model_dump(),
    )

    return ChartContextResponse(
        snapshot_id=snapshot_id,
        context=body,
        enriched=False,
        backend_context_version="1.0.0",
    )
