"""
Settings, notifications, and admin frontend configuration routes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.auth_dependencies import get_current_user, require_admin
from backend.models.settings import (
    AiHelperSettings,
    AlertSettings,
    AppSettingUpdateRequest,
    AppSettingsResponse,
    CustomizationDefaults,
    NotificationListResponse,
    NotificationPreferences,
    UserSettingsResponse,
)
from backend.services import settings_service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Get settings for the current user."""
    try:
        return await settings_service.get_user_settings(current_user["id"])
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )


@router.patch("/settings/notifications", response_model=UserSettingsResponse)
async def update_notification_settings(
    body: NotificationPreferences,
    current_user: dict = Depends(get_current_user),
):
    """Update notification preferences."""
    return await _update_settings(current_user["id"], "notification_preferences", body)


@router.patch("/settings/customization", response_model=UserSettingsResponse)
async def update_customization_defaults(
    body: CustomizationDefaults,
    current_user: dict = Depends(get_current_user),
):
    """Update customization defaults used on next reload/login."""
    return await _update_settings(current_user["id"], "customization_defaults", body)


@router.patch("/settings/ai", response_model=UserSettingsResponse)
async def update_ai_settings(
    body: AiHelperSettings,
    current_user: dict = Depends(get_current_user),
):
    """Update AI helper settings."""
    return await _update_settings(current_user["id"], "ai_settings", body)


@router.patch("/settings/alerts", response_model=UserSettingsResponse)
async def update_alert_settings(
    body: AlertSettings,
    current_user: dict = Depends(get_current_user),
):
    """Update alert settings."""
    return await _update_settings(current_user["id"], "alert_settings", body)


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    """List current user notifications."""
    try:
        payload = await settings_service.list_notifications(
            current_user["id"],
            limit=limit,
            unread_only=unread_only,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return NotificationListResponse(**payload)


@router.post("/notifications/read")
async def mark_notifications_read(
    notification_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Mark one notification or all notifications as read."""
    try:
        count = await settings_service.mark_notifications_read(
            current_user["id"],
            notification_id=notification_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return {"updated": count}


@router.get("/admin/app-settings", response_model=AppSettingsResponse)
async def get_app_settings(admin_user: dict = Depends(require_admin)):
    """Return app-wide settings for admin debug."""
    try:
        settings = await settings_service.get_app_settings()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return AppSettingsResponse(settings=settings)


@router.patch("/admin/app-settings/{key}", response_model=AppSettingsResponse)
async def update_app_setting(
    key: str,
    body: AppSettingUpdateRequest,
    admin_user: dict = Depends(require_admin),
):
    """Update one app-wide setting."""
    try:
        settings = await settings_service.update_app_setting(
            key=key,
            value=body.value,
            scope=body.scope,
            admin_user_id=admin_user["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return AppSettingsResponse(settings=settings)


async def _update_settings(
    user_id: str,
    field: str,
    body: object,
) -> UserSettingsResponse:
    """Shared settings update helper."""
    try:
        return await settings_service.update_user_settings(
            user_id,
            field,
            body.model_dump(),  # type: ignore[attr-defined]
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
