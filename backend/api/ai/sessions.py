"""
AI Sessions endpoints — list, create, get messages, and delete.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.auth_dependencies import get_current_user
from backend.models.ai.chat import AISessionCreateRequest, AISessionResponse
from backend.services import ai_chat_service

router = APIRouter()
logger = logging.getLogger("backend.api.ai.sessions")


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


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Soft-delete an AI chat session for the current user.

    Marks the session as ``deleted`` in PostgreSQL (matches the existing
    ``status`` check constraint). Messages are kept for audit but are
    excluded from ``GET /sessions`` because the list query already
    filters ``status != 'deleted'``.

    Returns ``{"deleted": true, "session_id": "..."}`` on success.
    """
    deleted = await ai_chat_service.soft_delete_session(
        session_id=session_id,
        user_id=current_user["id"],
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )
    return {"deleted": True, "session_id": session_id}
