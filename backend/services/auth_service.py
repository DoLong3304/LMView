"""
Auth service — handles registration, login, logout, and session management.

All database operations use asyncpg pool from backend.core.postgres.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from backend.core.postgres import get_pg_pool
from backend.core.security import (
    SESSION_EXPIRY_SECONDS,
    generate_session_token,
    hash_password,
    hash_session_token,
    validate_email,
    validate_password,
    verify_password,
)

logger = logging.getLogger("backend.services.auth_service")


async def register_user(
    email: str,
    password: str,
    display_name: str,
    preferred_language: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Tuple[dict, str, datetime]:
    """
    Register a new user and create an initial session.

    Returns:
        Tuple of (user_dict, raw_session_token, session_expires_at).

    Raises:
        ValueError: If email/password validation fails or email already exists.
        RuntimeError: If database is unavailable.
    """
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    email = validate_email(email)
    validate_password(password)
    pwd_hash = hash_password(password)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=SESSION_EXPIRY_SECONDS)
    raw_token, token_hash = generate_session_token()

    async with pool.acquire() as conn:
        # Check for existing user
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1", email
        )
        if existing:
            raise ValueError("Email already exists")

        # Create user
        user_row = await conn.fetchrow(
            """
            INSERT INTO users (email, display_name, password_hash, preferred_language, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $5)
            RETURNING id, email, display_name, role, preferred_language, timezone,
                      is_active, is_verified, created_at, last_login_at
            """,
            email, display_name, pwd_hash, preferred_language, now,
        )

        user_id = user_row["id"]

        # Create default preferences
        await conn.execute(
            """
            INSERT INTO user_preferences (user_id, preferred_language, created_at, updated_at)
            VALUES ($1, $2, $3, $3)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id, preferred_language, now,
        )

        # Create session
        await conn.execute(
            """
            INSERT INTO auth_sessions (user_id, session_token_hash, user_agent, ip_address, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id, token_hash, user_agent, ip_address, now, expires_at,
        )

    user_dict = {
        "id": str(user_row["id"]),
        "email": user_row["email"],
        "display_name": user_row["display_name"],
        "role": user_row["role"],
        "preferred_language": user_row["preferred_language"],
        "timezone": user_row["timezone"],
        "is_active": user_row["is_active"],
        "is_verified": user_row["is_verified"],
        "created_at": user_row["created_at"],
        "last_login_at": user_row["last_login_at"],
    }

    return user_dict, raw_token, expires_at


async def login_user(
    email: str,
    password: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Tuple[dict, str, datetime]:
    """
    Authenticate user and create a new session.

    Returns:
        Tuple of (user_dict, raw_session_token, session_expires_at).

    Raises:
        ValueError: If credentials are invalid.
        RuntimeError: If database is unavailable.
    """
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    email = validate_email(email)

    async with pool.acquire() as conn:
        user_row = await conn.fetchrow(
            """
            SELECT id, email, display_name, role, password_hash,
                   preferred_language, timezone, is_active, is_verified,
                   created_at, last_login_at
            FROM users
            WHERE email = $1
            """,
            email,
        )

    if user_row is None:
        raise ValueError("Invalid credentials")

    if not user_row["is_active"]:
        raise ValueError("Account is deactivated")

    if not verify_password(password, user_row["password_hash"]):
        raise ValueError("Invalid credentials")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=SESSION_EXPIRY_SECONDS)
    raw_token, token_hash = generate_session_token()

    async with pool.acquire() as conn:
        # Create session
        await conn.execute(
            """
            INSERT INTO auth_sessions (user_id, session_token_hash, user_agent, ip_address, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_row["id"], token_hash, user_agent, ip_address, now, expires_at,
        )
        # Update last_login_at
        await conn.execute(
            "UPDATE users SET last_login_at = $1 WHERE id = $2",
            now, user_row["id"],
        )

    user_dict = {
        "id": str(user_row["id"]),
        "email": user_row["email"],
        "display_name": user_row["display_name"],
        "role": user_row["role"],
        "preferred_language": user_row["preferred_language"],
        "timezone": user_row["timezone"],
        "is_active": user_row["is_active"],
        "is_verified": user_row["is_verified"],
        "created_at": user_row["created_at"],
        "last_login_at": now,
    }

    return user_dict, raw_token, expires_at


async def logout_session(session_id: str) -> bool:
    """
    Revoke a session by ID.

    Returns:
        True if session was revoked.
    """
    pool = await get_pg_pool()
    if pool is None:
        return False

    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE auth_sessions SET revoked_at = $1 WHERE id = $2 AND revoked_at IS NULL",
            now, session_id,
        )
    return "UPDATE 1" in result


async def get_user_with_preferences(user_id: str) -> Optional[dict]:
    """
    Get user data with preferences.

    Returns:
        Dict with user + preferences, or None.
    """
    pool = await get_pg_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        user_row = await conn.fetchrow(
            """
            SELECT id, email, display_name, role, preferred_language, timezone,
                   is_active, is_verified, created_at, last_login_at
            FROM users WHERE id = $1
            """,
            user_id if isinstance(user_id, str) is False else __import__("uuid").UUID(user_id),
        )
        if user_row is None:
            return None

        pref_row = await conn.fetchrow(
            "SELECT * FROM user_preferences WHERE user_id = $1",
            user_row["id"],
        )

    result = {
        "user": {
            "id": str(user_row["id"]),
            "email": user_row["email"],
            "display_name": user_row["display_name"],
            "role": user_row["role"],
            "preferred_language": user_row["preferred_language"],
            "timezone": user_row["timezone"],
            "is_active": user_row["is_active"],
            "is_verified": user_row["is_verified"],
            "created_at": user_row["created_at"],
            "last_login_at": user_row["last_login_at"],
        },
        "preferences": None,
    }

    if pref_row:
        fav_indicators = pref_row["favorite_indicators"]
        if isinstance(fav_indicators, str):
            fav_indicators = json.loads(fav_indicators)

        result["preferences"] = {
            "user_id": str(pref_row["user_id"]),
            "default_symbol": pref_row["default_symbol"],
            "default_timeframe": pref_row["default_timeframe"],
            "default_exchange": pref_row["default_exchange"],
            "preferred_language": pref_row["preferred_language"],
            "theme": pref_row["theme"],
            "risk_profile": pref_row["risk_profile"],
            "favorite_indicators": fav_indicators if isinstance(fav_indicators, list) else [],
            "ai_response_style": pref_row["ai_response_style"],
        }

    return result


async def update_preferences(user_id: str, updates: dict) -> Optional[dict]:
    """
    Update user preferences.

    Returns:
        Updated preferences dict, or None if user not found.
    """
    pool = await get_pg_pool()
    if pool is None:
        return None

    import uuid
    uid = uuid.UUID(user_id)
    now = datetime.now(timezone.utc)

    # Build SET clause dynamically from non-None fields
    allowed_fields = {
        "default_symbol", "default_timeframe", "default_exchange",
        "preferred_language", "theme", "risk_profile",
        "favorite_indicators", "ai_response_style",
    }

    set_parts = ["updated_at = $1"]
    from typing import Any
    values: list[Any] = [now]
    idx = 2

    for field, value in updates.items():
        if field in allowed_fields and value is not None:
            if field == "favorite_indicators":
                value = json.dumps(value) if isinstance(value, list) else value
            set_parts.append(f"{field} = ${idx}")
            values.append(value)
            idx += 1

    values.append(uid)

    async with pool.acquire() as conn:
        # Upsert preferences
        await conn.execute(
            f"""
            INSERT INTO user_preferences (user_id, created_at, updated_at)
            VALUES (${idx}, $1, $1)
            ON CONFLICT (user_id) DO UPDATE SET {', '.join(set_parts)}
            """,
            *values,
        )

        pref_row = await conn.fetchrow(
            "SELECT * FROM user_preferences WHERE user_id = $1", uid
        )

    if pref_row is None:
        return None

    fav_indicators = pref_row["favorite_indicators"]
    if isinstance(fav_indicators, str):
        fav_indicators = json.loads(fav_indicators)

    return {
        "user_id": str(pref_row["user_id"]),
        "default_symbol": pref_row["default_symbol"],
        "default_timeframe": pref_row["default_timeframe"],
        "default_exchange": pref_row["default_exchange"],
        "preferred_language": pref_row["preferred_language"],
        "theme": pref_row["theme"],
        "risk_profile": pref_row["risk_profile"],
        "favorite_indicators": fav_indicators if isinstance(fav_indicators, list) else [],
        "ai_response_style": pref_row["ai_response_style"],
    }
