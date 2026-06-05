"""
FastAPI dependencies for authentication.

Provides ``get_current_user`` dependency that resolves a valid session
from the Authorization header (Bearer token) and returns the user record.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from backend.core.postgres import get_pg_pool
from backend.core.security import hash_session_token

logger = logging.getLogger("backend.core.auth_dependencies")


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency: extract and validate session token from request.

    Looks for ``Authorization: Bearer <token>`` header.

    Returns:
        User dict with id, email, display_name, role, etc.

    Raises:
        HTTPException 401: If token is missing, invalid, or session expired.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = auth_header[7:]  # Strip "Bearer "
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty session token",
        )

    pool = await get_pg_pool()
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                u.id, u.email, u.username, u.display_name, u.avatar_url,
                u.date_of_birth, u.bio, u.role, u.preferred_language,
                u.timezone, u.is_active, u.is_verified,
                u.must_change_password, u.password_changed_at, u.deactivated_at,
                s.id AS session_id, s.expires_at, s.revoked_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.session_token_hash = $1
            """,
            token_hash,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )

    if row["revoked_at"] is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
        )

    if row["expires_at"] < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Update last_seen_at (fire-and-forget, don't block response)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE auth_sessions SET last_seen_at = $1 WHERE id = $2",
                now, row["session_id"],
            )
    except Exception:
        pass  # Non-critical

    return {
        "id": str(row["id"]),
        "email": row["email"],
        "username": row["username"],
        "display_name": row["display_name"],
        "avatar_url": row["avatar_url"],
        "date_of_birth": row["date_of_birth"],
        "bio": row["bio"],
        "role": row["role"],
        "preferred_language": row["preferred_language"],
        "timezone": row["timezone"],
        "is_active": row["is_active"],
        "is_verified": row["is_verified"],
        "must_change_password": row["must_change_password"],
        "password_changed_at": row["password_changed_at"],
        "deactivated_at": row["deactivated_at"],
        "session_id": str(row["session_id"]),
    }


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    FastAPI dependency: same as get_current_user but returns None
    instead of raising 401 when not authenticated.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require an active admin user."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    if current_user.get("must_change_password"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required before admin access",
        )
    return current_user
