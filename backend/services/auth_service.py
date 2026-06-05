"""
Auth service — handles registration, login, logout, and session management.

All database operations use asyncpg pool from backend.core.postgres.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

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

USER_RETURNING_FIELDS = """
    id, email, username, display_name, avatar_url, date_of_birth, bio, role,
    preferred_language, timezone, is_active, is_verified,
    must_change_password, password_changed_at, deactivated_at,
    created_at, last_login_at
"""


def _user_dict(row: Any, last_login_at: Optional[datetime] = None) -> dict:
    """Convert an asyncpg user row to the public user dict."""
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
        "created_at": row["created_at"],
        "last_login_at": last_login_at if last_login_at is not None else row["last_login_at"],
    }


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
            RETURNING
                id, email, username, display_name, avatar_url, date_of_birth,
                bio, role, preferred_language, timezone, is_active, is_verified,
                must_change_password, password_changed_at, deactivated_at,
                created_at, last_login_at
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

    return _user_dict(user_row), raw_token, expires_at


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
            SELECT id, email, username, display_name, avatar_url,
                   date_of_birth, bio, role, password_hash, preferred_language,
                   timezone, is_active, is_verified, must_change_password,
                   password_changed_at, deactivated_at, created_at, last_login_at
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

    return _user_dict(user_row, last_login_at=now), raw_token, expires_at


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
            SELECT id, email, username, display_name, avatar_url,
                   date_of_birth, bio, role, preferred_language, timezone,
                   is_active, is_verified, must_change_password,
                   password_changed_at, deactivated_at, created_at, last_login_at
            FROM users WHERE id = $1
            """,
            user_id if isinstance(user_id, str) is False else uuid.UUID(user_id),
        )
        if user_row is None:
            return None

        pref_row = await conn.fetchrow(
            "SELECT * FROM user_preferences WHERE user_id = $1",
            user_row["id"],
        )

    result = {
        "user": _user_dict(user_row),
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


async def update_profile(user_id: str, updates: dict) -> Optional[dict]:
    """Update mutable profile fields and return the safe user dict."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    allowed_fields = {
        "display_name",
        "username",
        "avatar_url",
        "date_of_birth",
        "bio",
        "preferred_language",
        "timezone",
    }
    filtered = {
        key: value
        for key, value in updates.items()
        if key in allowed_fields and value is not None
    }
    if not filtered:
        return await _get_user_only(user_id)

    now = datetime.now(timezone.utc)
    set_parts = ["updated_at = $1"]
    values: list[Any] = [now]
    idx = 2
    for field, value in filtered.items():
        if field == "username" and isinstance(value, str):
            value = value.strip().lower()
        set_parts.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    values.append(uuid.UUID(user_id))

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE users
                SET {', '.join(set_parts)}
                WHERE id = ${idx}
                RETURNING
                    id, email, username, display_name, avatar_url,
                    date_of_birth, bio, role, preferred_language, timezone,
                    is_active, is_verified, must_change_password,
                    password_changed_at, deactivated_at, created_at, last_login_at
                """,
                *values,
            )
    except Exception as exc:
        if "users_username_key" in str(exc):
            raise ValueError("Username already exists") from exc
        raise

    return _user_dict(row) if row else None


async def change_password(
    user_id: str,
    current_password: str,
    new_password: str,
) -> Optional[dict]:
    """Change password after verifying the current password."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    validate_password(new_password)
    uid = uuid.UUID(user_id)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT password_hash FROM users WHERE id = $1 AND is_active = TRUE",
            uid,
        )
        if row is None:
            return None
        if not verify_password(current_password, row["password_hash"]):
            raise ValueError("Current password is incorrect")

        now = datetime.now(timezone.utc)
        updated = await conn.fetchrow(
            """
            UPDATE users
            SET password_hash = $1,
                must_change_password = FALSE,
                password_changed_at = $2,
                updated_at = $2
            WHERE id = $3
            RETURNING
                id, email, username, display_name, avatar_url,
                date_of_birth, bio, role, preferred_language, timezone,
                is_active, is_verified, must_change_password,
                password_changed_at, deactivated_at, created_at, last_login_at
            """,
            hash_password(new_password),
            now,
            uid,
        )

    return _user_dict(updated) if updated else None


async def deactivate_account(user_id: str, confirmation: str) -> bool:
    """Soft-deactivate the current account and revoke sessions."""
    if confirmation.strip().upper() != "DELETE":
        raise ValueError("Confirmation must be DELETE")

    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    uid = uuid.UUID(user_id)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        user_role = await conn.fetchval("SELECT role FROM users WHERE id = $1", uid)
        if user_role == "admin":
            active_admins = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = TRUE"
            )
            if active_admins <= 1:
                raise ValueError("Cannot deactivate the final active admin")

        result = await conn.execute(
            """
            UPDATE users
            SET is_active = FALSE, deactivated_at = $1, updated_at = $1
            WHERE id = $2 AND is_active = TRUE
            """,
            now,
            uid,
        )
        await conn.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = $1
            WHERE user_id = $2 AND revoked_at IS NULL
            """,
            now,
            uid,
        )

    return "UPDATE 1" in result


async def _get_user_only(user_id: str) -> Optional[dict]:
    """Fetch a safe user dict without preferences."""
    pool = await get_pg_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, username, display_name, avatar_url,
                   date_of_birth, bio, role, preferred_language, timezone,
                   is_active, is_verified, must_change_password,
                   password_changed_at, deactivated_at, created_at, last_login_at
            FROM users
            WHERE id = $1
            """,
            uuid.UUID(user_id),
        )
    return _user_dict(row) if row else None
