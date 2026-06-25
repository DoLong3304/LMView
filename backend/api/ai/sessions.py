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


@router.post("/sessions/{session_id}/messages", status_code=status.HTTP_201_CREATED)
async def post_message(
    session_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Persist a non-LLM message (e.g. tour recap) to an existing session.

    Used by the frontend after a guided tour completes so the recap
    bubble + Replay button survive a page reload. The body MUST include
    ``role`` ("assistant") and ``content`` (recap text). Optional:
    ``metadata`` (dict) for tour flags / tool_calls.
    """
    from ai_service.persistence import chat_store
    role = body.get("role")
    content = body.get("content")
    if role not in ("assistant", "user", "system"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role must be assistant|user|system",
        )
    if not content or not isinstance(content, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content must be a non-empty string",
        )
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    stored = await chat_store.store_message(
        session_id=session_id,
        user_id=current_user["id"],
        role=role,
        content=content,
        model_provider="tour_recap",
        model_name="tour_recap",
        metadata=metadata,
    )
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist message",
        )
    return {"message": stored}


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
