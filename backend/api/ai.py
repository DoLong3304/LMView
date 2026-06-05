"""
AI API — foundation endpoints for Phase 0.

All endpoints require authentication except /api/ai/health.
Phase 0 returns deterministic mock responses, not real LLM output.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.auth_dependencies import get_current_user, get_optional_user
from backend.core.postgres import pg_health_check
from backend.models.ai import (
    AIChatRequest,
    AIChatResponse,
    AIChartAction,
    AIChartActionRecordRequest,
    AIChartActionType,
    AIChartActionValidateRequest,
    AIChartActionValidationResult,
    AIHealthResponse,
    AIMessageResponse,
    AISessionCreateRequest,
    AISessionResponse,
)
from backend.models.chart_context import ChartContextDTO, ChartContextResponse
from backend.services import ai_action_service, ai_chat_service, ai_mock_service
from backend.services.scope_gate_service import check_scope

router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = logging.getLogger("backend.api.ai")


@router.get("/health", response_model=AIHealthResponse)
async def ai_health(user: dict | None = Depends(get_optional_user)):
    """Check AI foundation status. Does not call LLM."""
    pg_status = await pg_health_check()
    db_ready = pg_status.get("status") == "healthy"

    return AIHealthResponse(
        auth_required=True,
        database_ready=db_ready,
        mock_mode_available=True,
        chart_action_schema_version="1.1.0",
        supported_modes=["ask", "interact"],
        supported_action_types=[t.value for t in AIChartActionType],
    )


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message to the AI assistant.

    Phase 0: returns a deterministic mock response that proves wiring.
    Stores user and assistant messages in PostgreSQL.
    """
    user_id = current_user["id"]

    # Scope gate check
    scope_result = check_scope(body.message)
    if not scope_result.in_scope:
        return AIChatResponse(
            session_id=body.session_id or "",
            message_id="",
            role="assistant",
            content=(
                "I can only help with cryptocurrency market analysis, "
                "technical indicators, chart interaction, and LMView platform usage. "
                f"Reason: {scope_result.reason}"
            ),
            provider="scope_gate",
            is_mock=True,
            warnings=[f"Message classified as out-of-scope: {scope_result.category.value}"],
        )

    # Create or use existing session
    session_id = body.session_id
    if not session_id:
        session = await ai_chat_service.create_session(
            user_id=user_id,
            mode=body.mode.value,
            symbol=body.chart_context.get("symbol") if body.chart_context else None,
            timeframe=body.chart_context.get("timeframe") if body.chart_context else None,
            exchange=body.chart_context.get("exchange", "binance") if body.chart_context else "binance",
        )
        if session:
            session_id = session["id"]
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not create AI session — database may be unavailable",
            )

    # Store user message
    user_msg = await ai_chat_service.store_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=body.message,
        metadata={"language": body.language, "scope": scope_result.model_dump()},
    )

    # Generate Phase 0 mock response
    mock_result = ai_mock_service.generate_mock_response(
        message=body.message,
        mode=body.mode.value,
        chart_context=body.chart_context,
        language=body.language,
    )

    # Store assistant message
    assistant_msg = await ai_chat_service.store_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=mock_result["content"],
        model_provider=mock_result["provider"],
        metadata={"is_mock": True, "grounded_context_used": mock_result["grounded_context_used"]},
    )

    message_id = assistant_msg["id"] if assistant_msg else ""

    return AIChatResponse(
        session_id=session_id,
        message_id=message_id,
        role="assistant",
        content=mock_result["content"],
        provider=mock_result["provider"],
        model_name=mock_result["model_name"],
        is_mock=mock_result["is_mock"],
        created_at=datetime.now(timezone.utc),
        warnings=mock_result["warnings"],
        suggested_actions=mock_result["suggested_actions"],
        chart_actions=mock_result["chart_actions"],
        grounded_context_used=mock_result["grounded_context_used"],
    )


@router.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """List AI chat sessions for the current user."""
    sessions = await ai_chat_service.get_sessions(current_user["id"])
    return {"sessions": sessions}


@router.post("/sessions", response_model=AISessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: AISessionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new AI chat session."""
    session = await ai_chat_service.create_session(
        user_id=current_user["id"],
        mode=body.mode.value,
        title=body.title,
        symbol=body.symbol,
        timeframe=body.timeframe,
        exchange=body.exchange or "binance",
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create session",
        )
    return AISessionResponse(**session)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get messages for a specific AI session."""
    messages = await ai_chat_service.get_session_messages(
        session_id=session_id,
        user_id=current_user["id"],
    )
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )
    return {"messages": messages}


@router.post("/chart-context", response_model=ChartContextResponse)
async def submit_chart_context(
    body: ChartContextDTO,
    current_user: dict = Depends(get_current_user),
):
    """Accept and store a chart context snapshot from the frontend."""
    snapshot_id = await ai_chat_service.store_chart_snapshot(
        user_id=current_user["id"],
        session_id=None,  # Can be linked to a session later
        context=body.model_dump(),
    )

    return ChartContextResponse(
        snapshot_id=snapshot_id,
        context=body,
        enriched=False,
        backend_context_version="1.0.0",
    )


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
    # Validate allowed status values
    if body.approval_status and body.approval_status not in {
        "approved", "rejected", "edited"
    }:
        raise HTTPException(400, "Invalid approval_status")
    if body.execution_status and body.execution_status not in {
        "executed", "failed"
    }:
        raise HTTPException(400, "Invalid execution_status")

    # For Phase 0, we just acknowledge — full action recording requires
    # the action to have been created first via validate
    return {
        "recorded": True,
        "action_id": body.action_id,
        "approval_status": body.approval_status,
        "execution_status": body.execution_status,
    }
