"""
Pydantic models for user settings, notifications, and admin account tools.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.auth import UserResponse


class NotificationPreferences(BaseModel):
    """User-controlled notification display channels."""
    system: bool = True
    alerts: bool = True
    news: bool = True
    ai: bool = True
    sound: bool = False
    desktop: bool = False
    email: bool = False
    position: str = "top-right"


class CustomizationDefaults(BaseModel):
    """Defaults applied on fresh login/reload, not immediate transient state."""
    theme: str = "dark"
    default_timeframe: str = "1m"
    default_chart_type: str = "candles"
    default_symbol: str = "BTCUSDT"
    default_exchange: str = "binance"
    visible_indicators: List[str] = Field(default_factory=list)
    drawing_defaults: Dict[str, Any] = Field(default_factory=dict)


class AiHelperSettings(BaseModel):
    """AI-helper settings for future agent behavior."""
    response_style: str = "concise"
    risk_reminders: bool = True
    auto_include_chart_context: bool = True
    allow_chart_actions: bool = False
    require_action_confirmation: bool = True
    max_context_candles: int = Field(300, ge=50, le=2000)
    memory_retention_days: int = Field(30, ge=1, le=365)


class AlertSettings(BaseModel):
    """Alert notification settings."""
    price_alerts: bool = True
    volume_alerts: bool = True
    indicator_alerts: bool = True
    whale_alerts: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"


class UserSettingsResponse(BaseModel):
    """Bundled settings payload for the frontend settings modal."""
    notification_preferences: NotificationPreferences = Field(
        default_factory=NotificationPreferences
    )
    customization_defaults: CustomizationDefaults = Field(
        default_factory=CustomizationDefaults
    )
    ai_settings: AiHelperSettings = Field(default_factory=AiHelperSettings)
    alert_settings: AlertSettings = Field(default_factory=AlertSettings)


class NotificationResponse(BaseModel):
    """Single notification for the header popup."""
    id: str
    category: str
    severity: str
    title: str
    body: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Notification list plus unread count."""
    notifications: List[NotificationResponse]
    unread_count: int


class AdminUserUpdateRequest(BaseModel):
    """Admin mutation for role and active status."""
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AdminUsersResponse(BaseModel):
    """Paginated admin user list."""
    users: List[UserResponse]
    total: int
    limit: int
    offset: int


class AppSettingUpdateRequest(BaseModel):
    """Admin update for one global app setting."""
    value: Any
    scope: str = "frontend"


class AppSettingsResponse(BaseModel):
    """Global settings visible in admin debug."""
    settings: Dict[str, Any]
