"""
AI Chart Actions endpoints — validate and record chart actions.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chart_actions import (
    AIChartActionRecordRequest,
    AIChartActionValidateRequest,
    AIChartActionValidationResult,
)
from backend.services import ai_action_service

router = APIRouter()
logger = logging.getLogger("backend.api.ai.chart_actions")


@router.post("/chart-actions/validate", response_model=AIChartActionValidationResult)
async def validate_chart_actions(
    body: AIChartActionValidateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Validate proposed chart actions without executing them."""
    result = ai_action_service.validate_actions(body.actions)

    return AIChartActionValidationResult(
        valid=result["valid"],
        errors=result["errors"],
        warnings=result["warnings"],
        validated_actions=result["validated_actions"],
    )


@router.post("/chart-actions/record")
async def record_chart_action(
    body: AIChartActionRecordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Record approval/rejection/execution state of a chart action."""
    if body.approval_status and body.approval_status not in {
        "approved", "rejected", "edited"
    }:
        raise HTTPException(400, "Invalid approval_status")
    if body.execution_status and body.execution_status not in {
        "executed", "failed"
    }:
        raise HTTPException(400, "Invalid execution_status")

    return {
        "recorded": True,
        "action_id": body.action_id,
        "approval_status": body.approval_status,
        "execution_status": body.execution_status,
    }
