"""
Pydantic models for authentication and user management.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Request models ────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """User registration request."""
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    preferred_language: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request."""
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UpdatePreferencesRequest(BaseModel):
    """Update user preferences."""
    default_symbol: Optional[str] = None
    default_timeframe: Optional[str] = None
    default_exchange: Optional[str] = None
    preferred_language: Optional[str] = None
    theme: Optional[str] = None
    risk_profile: Optional[str] = None
    favorite_indicators: Optional[List[str]] = None
    ai_response_style: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    """Update account profile fields."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=40)
    avatar_url: Optional[str] = Field(None, max_length=1000)
    date_of_birth: Optional[date] = None
    bio: Optional[str] = Field(None, max_length=500)
    preferred_language: Optional[str] = Field(None, max_length=16)
    timezone: Optional[str] = Field(None, max_length=80)


class ChangePasswordRequest(BaseModel):
    """Change the current user's password."""
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class DeleteAccountRequest(BaseModel):
    """Deactivate the current user's account after explicit confirmation."""
    confirmation: str = Field(..., min_length=1, max_length=32)


# ── Response models ───────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Safe user representation (no password hash)."""
    id: str
    email: str
    username: Optional[str] = None
    display_name: str
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    bio: Optional[str] = None
    role: str = "user"
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    must_change_password: bool = False
    password_changed_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class SessionInfo(BaseModel):
    """Session metadata returned to client."""
    session_token: str  # Raw token — only returned once at login/register
    expires_at: datetime


class AuthResponse(BaseModel):
    """Response for login/register endpoints."""
    user: UserResponse
    session: SessionInfo


class UserPreferencesResponse(BaseModel):
    """User preferences."""
    user_id: str
    default_symbol: Optional[str] = None
    default_timeframe: Optional[str] = None
    default_exchange: Optional[str] = "binance"
    preferred_language: Optional[str] = None
    theme: Optional[str] = None
    risk_profile: Optional[str] = None
    favorite_indicators: List[str] = Field(default_factory=list)
    ai_response_style: Optional[str] = None


class MeResponse(BaseModel):
    """Response for /api/auth/me — user + preferences."""
    user: UserResponse
    preferences: Optional[UserPreferencesResponse] = None
