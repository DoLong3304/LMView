"""
Settings and notifications service.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.core.postgres import get_pg_pool
from backend.models.settings import (
    AiHelperSettings,
    AlertSettings,
    CustomizationDefaults,
    NotificationPreferences,
    UserSettingsResponse,
)


def _json_obj(value: Any, default: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict from asyncpg JSON/JSONB values."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else default
        except json.JSONDecodeError:
            return default
    return default


def _json_value(value: Any) -> Any:
    """Return a JSON/JSONB value from asyncpg without forcing object shape."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


async def get_user_settings(user_id: str) -> UserSettingsResponse:
    """Fetch or create user settings."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    uid = uuid.UUID(user_id)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_preferences (user_id, created_at, updated_at)
            VALUES ($1, now(), now())
            ON CONFLICT (user_id) DO NOTHING
            """,
            uid,
        )
        row = await conn.fetchrow(
            """
            SELECT notification_preferences, customization_defaults,
                   ai_settings, alert_settings
            FROM user_preferences
            WHERE user_id = $1
            """,
            uid,
        )

    if row is None:
        return UserSettingsResponse()

    return UserSettingsResponse(
        notification_preferences=NotificationPreferences(
            **_json_obj(row["notification_preferences"], {})
        ),
        customization_defaults=CustomizationDefaults(
            **_json_obj(row["customization_defaults"], {})
        ),
        ai_settings=AiHelperSettings(**_json_obj(row["ai_settings"], {})),
        alert_settings=AlertSettings(**_json_obj(row["alert_settings"], {})),
    )


async def update_user_settings(
    user_id: str,
    field: str,
    value: Dict[str, Any],
) -> UserSettingsResponse:
    """Patch one JSON settings field and return the complete settings bundle."""
    if field not in {
        "notification_preferences",
        "customization_defaults",
        "ai_settings",
        "alert_settings",
    }:
        raise ValueError("Unsupported settings field")

    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    current = await get_user_settings(user_id)
    current_value = getattr(current, field).model_dump()
    current_value.update(value)

    if field == "notification_preferences":
        model = NotificationPreferences(**current_value)
    elif field == "customization_defaults":
        model = CustomizationDefaults(**current_value)
    elif field == "ai_settings":
        model = AiHelperSettings(**current_value)
    else:
        model = AlertSettings(**current_value)

    uid = uuid.UUID(user_id)
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO user_preferences (user_id, {field}, created_at, updated_at)
            VALUES ($1, $2::jsonb, now(), now())
            ON CONFLICT (user_id) DO UPDATE
            SET {field} = $2::jsonb, updated_at = now()
            """,
            uid,
            json.dumps(model.model_dump()),
        )

    return await get_user_settings(user_id)


async def list_notifications(
    user_id: str,
    limit: int = 20,
    unread_only: bool = False,
) -> dict:
    """List notifications for a user with unread count."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    uid = uuid.UUID(user_id)
    limit = max(1, min(limit, 100))
    where = "user_id = $1"
    if unread_only:
        where += " AND read_at IS NULL"

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, category, severity, title, body, payload, read_at, created_at
            FROM user_notifications
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT $2
            """,
            uid,
            limit,
        )
        unread_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM user_notifications
            WHERE user_id = $1 AND read_at IS NULL
            """,
            uid,
        )

    return {
        "notifications": [
            {
                "id": str(row["id"]),
                "category": row["category"],
                "severity": row["severity"],
                "title": row["title"],
                "body": row["body"],
                "payload": _json_obj(row["payload"], {}),
                "read_at": row["read_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ],
        "unread_count": int(unread_count or 0),
    }


async def mark_notifications_read(
    user_id: str,
    notification_id: Optional[str] = None,
) -> int:
    """Mark one or all notifications as read."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    uid = uuid.UUID(user_id)
    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        if notification_id:
            result = await conn.execute(
                """
                UPDATE user_notifications
                SET read_at = COALESCE(read_at, $1)
                WHERE user_id = $2 AND id = $3
                """,
                now,
                uid,
                uuid.UUID(notification_id),
            )
        else:
            result = await conn.execute(
                """
                UPDATE user_notifications
                SET read_at = COALESCE(read_at, $1)
                WHERE user_id = $2 AND read_at IS NULL
                """,
                now,
                uid,
            )
    return int(result.split()[-1]) if result.startswith("UPDATE") else 0


async def get_app_settings() -> Dict[str, Any]:
    """Return app-wide settings keyed by setting name."""
    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM app_settings ORDER BY key")
    return {row["key"]: _json_value(row["value"]) for row in rows}


async def update_app_setting(
    key: str,
    value: Any,
    scope: str,
    admin_user_id: str,
) -> Dict[str, Any]:
    """Update one app-wide setting."""
    if scope not in {"frontend", "backend", "system"}:
        raise ValueError("Invalid setting scope")

    pool = await get_pg_pool()
    if pool is None:
        raise RuntimeError("Database unavailable")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, scope, updated_by, updated_at)
            VALUES ($1, $2::jsonb, $3, $4, now())
            ON CONFLICT (key) DO UPDATE
            SET value = $2::jsonb,
                scope = $3,
                updated_by = $4,
                updated_at = now()
            """,
            key,
            json.dumps(value),
            scope,
            uuid.UUID(admin_user_id),
        )
    return await get_app_settings()
