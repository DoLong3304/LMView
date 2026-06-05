"""
Default admin bootstrap service.

Creates or recovers an admin account only when no active admin exists.
Credentials are environment-driven and never logged.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from backend.core.postgres import get_pg_pool
from backend.core.security import hash_password, validate_email, validate_password

logger = logging.getLogger("backend.services.admin_bootstrap_service")


async def ensure_default_admin() -> None:
    """Create or recover the default admin account when no active admin exists."""
    pool = await get_pg_pool()
    if pool is None:
        logger.warning("Default admin bootstrap skipped: PostgreSQL unavailable")
        return

    email = os.environ.get("DEFAULT_ADMIN_EMAIL", "").strip()
    initial_password = os.environ.get("DEFAULT_ADMIN_INITIAL_PASSWORD", "")
    display_name = os.environ.get("DEFAULT_ADMIN_DISPLAY_NAME", "LMView Admin").strip()
    username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin").strip().lower()

    async with pool.acquire() as conn:
        active_admin_count = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = TRUE"
        )
        if active_admin_count and active_admin_count > 0:
            return

    if not email or not initial_password:
        logger.warning(
            "No active admin exists, but DEFAULT_ADMIN_EMAIL or "
            "DEFAULT_ADMIN_INITIAL_PASSWORD is not configured"
        )
        return

    try:
        email = validate_email(email)
        validate_password(initial_password)
    except ValueError as exc:
        logger.warning("Default admin bootstrap skipped: %s", exc)
        return

    now = datetime.now(timezone.utc)
    password_hash = hash_password(initial_password)

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            email,
        )

        if existing:
            await conn.execute(
                """
                UPDATE users
                SET role = 'admin',
                    password_hash = $1,
                    display_name = COALESCE(NULLIF(display_name, ''), $2),
                    username = COALESCE(username, $3),
                    is_active = TRUE,
                    is_verified = TRUE,
                    must_change_password = TRUE,
                    created_by_system = TRUE,
                    deactivated_at = NULL,
                    updated_at = $4
                WHERE id = $5
                """,
                password_hash,
                display_name or "LMView Admin",
                await _available_username(conn, username, existing["id"]),
                now,
                existing["id"],
            )
            logger.info("Default admin account recovered from configured email")
            return

        created = await conn.fetchrow(
            """
            INSERT INTO users (
                email, username, display_name, password_hash, role,
                is_active, is_verified, must_change_password,
                created_by_system, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, 'admin', TRUE, TRUE, TRUE, TRUE, $5, $5)
            RETURNING id
            """,
            email,
            await _available_username(conn, username, None),
            display_name or "LMView Admin",
            password_hash,
            now,
        )
        await conn.execute(
            """
            INSERT INTO user_preferences (user_id, created_at, updated_at)
            VALUES ($1, $2, $2)
            ON CONFLICT (user_id) DO NOTHING
            """,
            created["id"],
            now,
        )

    logger.info("Default admin account created from configured email")


async def _available_username(conn, preferred: str, existing_user_id: Optional[str]):
    """Return preferred username if available, otherwise NULL."""
    if not preferred:
        return None
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE username = $1",
        preferred,
    )
    if row is None:
        return preferred
    if existing_user_id is not None and row["id"] == existing_user_id:
        return preferred
    return None
