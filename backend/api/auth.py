"""
Auth API — thin route handlers for user authentication.

Business logic lives in ``backend.services.auth_service``.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.core.auth_dependencies import get_current_user
from backend.models.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    SessionInfo,
    UpdatePreferencesRequest,
    UserPreferencesResponse,
    UserResponse,
)
from backend.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("backend.api.auth")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request):
    """Register a new user account."""
    try:
        user_dict, raw_token, expires_at = await auth_service.register_user(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            preferred_language=body.preferred_language,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return AuthResponse(
        user=UserResponse(**user_dict),
        session=SessionInfo(session_token=raw_token, expires_at=expires_at),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request):
    """Authenticate with email and password."""
    try:
        user_dict, raw_token, expires_at = await auth_service.login_user(
            email=body.email,
            password=body.password,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return AuthResponse(
        user=UserResponse(**user_dict),
        session=SessionInfo(session_token=raw_token, expires_at=expires_at),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: dict = Depends(get_current_user)):
    """Revoke the current session."""
    session_id = current_user.get("session_id")
    if session_id:
        await auth_service.logout_session(session_id)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user and preferences."""
    result = await auth_service.get_user_with_preferences(current_user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_resp = UserResponse(**result["user"])
    prefs_resp = None
    if result.get("preferences"):
        prefs_resp = UserPreferencesResponse(**result["preferences"])

    return MeResponse(user=user_resp, preferences=prefs_resp)


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    body: UpdatePreferencesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user preferences."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    result = await auth_service.update_preferences(current_user["id"], updates)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserPreferencesResponse(**result)
