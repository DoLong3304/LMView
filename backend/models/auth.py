"""
Pydantic models for authentication and user management.
"""
from __future__ import annotations

from datetime import datetime
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


# ── Response models ───────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Safe user representation (no password hash)."""
    id: str
    email: str
    display_name: str
    role: str = "user"
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
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
