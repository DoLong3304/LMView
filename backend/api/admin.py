"""
Admin-only account management routes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.auth_dependencies import require_admin
from backend.models.auth import UserResponse
from backend.models.settings import AdminUserUpdateRequest, AdminUsersResponse
from backend.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    query: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: dict = Depends(require_admin),
):
    """List/search users for admin account management."""
    try:
        payload = await admin_service.list_users(
            query=query,
            role=role,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return AdminUsersResponse(**payload)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: AdminUserUpdateRequest,
    admin_user: dict = Depends(require_admin),
):
    """Update a user's role or active state."""
    try:
        user = await admin_service.update_user_access(
            user_id,
            role=body.role,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)


@router.post("/users/{user_id}/force-password-change", response_model=UserResponse)
async def force_password_change(
    user_id: str,
    admin_user: dict = Depends(require_admin),
):
    """Force password change for a user."""
    try:
        user = await admin_service.force_password_change(user_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)
