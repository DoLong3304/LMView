"""
Admin account-management service.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.core.postgres import get_pg_pool

ALLOWED_ROLES = {"user", "moderator", "admin"}


def _user_dict(row: Any) -> dict:
    """Convert a DB user row to the public user shape."""
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
        "last_login_at": row["last_login_at"],
    }


async def list_users(
    query: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List users for admin account management."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    clauses = ["TRUE"]
    values: list[Any] = []
    idx = 1

    if query:
        clauses.append(
            f"(email ILIKE ${idx} OR display_name ILIKE ${idx} OR username ILIKE ${idx})"
        )
        values.append(f"%{query.strip()}%")
        idx += 1
    if role:
        if role not in ALLOWED_ROLES:
            raise ValueError("Invalid role")
        clauses.append(f"role = ${idx}")
        values.append(role)
        idx += 1
    if is_active is not None:
        clauses.append(f"is_active = ${idx}")
        values.append(is_active)
        idx += 1

    where_sql = " AND ".join(clauses)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, email, username, display_name, avatar_url,
                   date_of_birth, bio, role, preferred_language, timezone,
                   is_active, is_verified, must_change_password,
                   password_changed_at, deactivated_at, created_at, last_login_at
            FROM users
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *values,
            limit,
            offset,
        )
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM users WHERE {where_sql}",
            *values,
        )

    return {
        "users": [_user_dict(row) for row in rows],
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
    }


async def update_user_access(
    target_user_id: str,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[dict]:
    """Update role/active status for a user."""
    if role is not None and role not in ALLOWED_ROLES:
        raise ValueError("Invalid role")
    if role is None and is_active is None:
        raise ValueError("No fields to update")

    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    target_id = uuid.UUID(target_user_id)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, role, is_active FROM users WHERE id = $1",
            target_id,
        )
        if existing is None:
            return None

        final_admin_risk = (
            existing["role"] == "admin"
            and existing["is_active"]
            and ((role is not None and role != "admin") or is_active is False)
        )
        if final_admin_risk:
            active_admins = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = TRUE"
            )
            if active_admins <= 1:
                raise ValueError("Cannot remove the final active admin")

        set_parts = ["updated_at = $1"]
        values: list[Any] = [now]
        idx = 2
        if role is not None:
            set_parts.append(f"role = ${idx}")
            values.append(role)
            idx += 1
        if is_active is not None:
            set_parts.append(f"is_active = ${idx}")
            values.append(is_active)
            idx += 1
            set_parts.append(
                f"deactivated_at = CASE WHEN ${idx - 1} = FALSE THEN $1 ELSE NULL END"
            )

        values.append(target_id)
        row = await conn.fetchrow(
            f"""
            UPDATE users
            SET {', '.join(set_parts)}
            WHERE id = ${idx}
            RETURNING id, email, username, display_name, avatar_url,
                      date_of_birth, bio, role, preferred_language, timezone,
                      is_active, is_verified, must_change_password,
                      password_changed_at, deactivated_at, created_at, last_login_at
            """,
            *values,
        )

    return _user_dict(row) if row else None


async def force_password_change(target_user_id: str) -> Optional[dict]:
    """Force a user to change password on next login/session restore."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET must_change_password = TRUE, updated_at = $1
            WHERE id = $2
            RETURNING id, email, username, display_name, avatar_url,
                      date_of_birth, bio, role, preferred_language, timezone,
                      is_active, is_verified, must_change_password,
                      password_changed_at, deactivated_at, created_at, last_login_at
            """,
            now,
            uuid.UUID(target_user_id),
        )

    return _user_dict(row) if row else None
