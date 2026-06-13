"""
Notification creation service.

Creates notifications for users, respecting user preferences and categories.
Works alongside settings_service.py which handles listing and mark-as-read.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.postgres import get_pg_pool

logger = logging.getLogger(__name__)

# ── Notification categories ───────────────────────────────────────────────────
VALID_CATEGORIES = {"system", "alert", "news", "ai"}
VALID_SEVERITIES = {"info", "success", "warning", "error"}


async def create_notification(
    user_id: str,
    category: str,
    title: str,
    body: Optional[str] = None,
    severity: str = "info",
    payload: Optional[Dict[str, Any]] = None,
    respect_preferences: bool = True,
) -> Optional[str]:
    """
    Create a notification for a specific user.

    Args:
        user_id: Target user UUID.
        category: One of 'system', 'alert', 'news', 'ai'.
        title: Notification title.
        body: Optional notification body text.
        severity: One of 'info', 'success', 'warning', 'error'.
        payload: Optional JSON payload with extra data.
        respect_preferences: If True, check user notification preferences.

    Returns:
        Notification ID string, or None if notification was filtered/failed.
    """
    if category not in VALID_CATEGORIES:
        logger.warning("Invalid notification category: %s", category)
        return None

    if severity not in VALID_SEVERITIES:
        severity = "info"

    pool = await get_pg_pool()
    if pool is None:
        logger.warning("Cannot create notification — database unavailable")
        return None

    uid = uuid.UUID(user_id)

    # Check user preferences if requested
    if respect_preferences:
        allowed = await _check_user_preference(pool, uid, category)
        if not allowed:
            logger.debug(
                "Notification suppressed for user %s category %s (preference disabled)",
                user_id[:8], category,
            )
            return None

    try:
        async with pool.acquire() as conn:
            notification_id = await conn.fetchval(
                """
                INSERT INTO user_notifications (user_id, category, severity, title, body, payload)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                RETURNING id
                """,
                uid,
                category,
                severity,
                title[:500],  # Cap title length
                (body or "")[:2000],  # Cap body length
                json.dumps(payload or {}),
            )
        logger.debug("Created notification %s for user %s", notification_id, user_id[:8])
        return str(notification_id)

    except Exception as exc:
        logger.warning("Failed to create notification: %s", exc)
        return None


async def create_notification_for_users(
    user_ids: List[str],
    category: str,
    title: str,
    body: Optional[str] = None,
    severity: str = "info",
    payload: Optional[Dict[str, Any]] = None,
    respect_preferences: bool = True,
) -> int:
    """
    Create the same notification for multiple users.

    Returns:
        Count of notifications successfully created.
    """
    created = 0
    for uid in user_ids:
        result = await create_notification(
            user_id=uid,
            category=category,
            title=title,
            body=body,
            severity=severity,
            payload=payload,
            respect_preferences=respect_preferences,
        )
        if result:
            created += 1
    return created


async def create_notification_for_all_admins(
    category: str,
    title: str,
    body: Optional[str] = None,
    severity: str = "info",
    payload: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Create a notification for all active admin users.

    Returns:
        Count of notifications created.
    """
    pool = await get_pg_pool()
    if pool is None:
        return 0

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM users WHERE role = 'admin' AND is_active = TRUE"
            )
        admin_ids = [str(row["id"]) for row in rows]
        return await create_notification_for_users(
            user_ids=admin_ids,
            category=category,
            title=title,
            body=body,
            severity=severity,
            payload=payload,
            respect_preferences=False,  # Always notify admins for system events
        )

    except Exception as exc:
        logger.warning("Failed to create admin notifications: %s", exc)
        return 0


# ── Event-specific helpers ────────────────────────────────────────────────────

async def notify_ai_action_completed(
    user_id: str,
    action_type: str,
    success: bool,
    details: Optional[str] = None,
) -> Optional[str]:
    """Notify user when an AI action completes or fails."""
    if success:
        title = f"AI action completed: {action_type}"
        severity = "success"
    else:
        title = f"AI action failed: {action_type}"
        severity = "error"

    return await create_notification(
        user_id=user_id,
        category="ai",
        title=title,
        body=details,
        severity=severity,
        payload={"action_type": action_type, "success": success},
    )


async def notify_news_risk_event(
    user_id: str,
    symbol: str,
    headline: str,
    sentiment_label: str,
    source: str,
) -> Optional[str]:
    """Notify user when a risk-related news event is detected for a watched symbol."""
    return await create_notification(
        user_id=user_id,
        category="news",
        title=f"News alert: {symbol}",
        body=f"{headline} [{source}]",
        severity="warning",
        payload={
            "symbol": symbol,
            "headline": headline[:200],
            "sentiment": sentiment_label,
            "source": source,
        },
    )


async def notify_system_degraded(
    component: str,
    message: str,
) -> int:
    """Notify all admins when a system component is degraded."""
    return await create_notification_for_all_admins(
        category="system",
        title=f"System degraded: {component}",
        body=message,
        severity="warning",
        payload={"component": component},
    )


async def notify_alert_triggered(
    user_id: str,
    symbol: str,
    alert_type: str,
    alert_message: str,
    current_price: Optional[float] = None,
) -> Optional[str]:
    """Notify user when a price/indicator/volume alert triggers."""
    return await create_notification(
        user_id=user_id,
        category="alert",
        title=f"Alert triggered: {symbol} ({alert_type})",
        body=alert_message,
        severity="warning",
        payload={
            "symbol": symbol,
            "alert_type": alert_type,
            "current_price": current_price,
        },
    )


# ── Preference checking ──────────────────────────────────────────────────────

async def _check_user_preference(pool, user_id: uuid.UUID, category: str) -> bool:
    """Check if user has the notification category enabled."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT notification_preferences FROM user_preferences WHERE user_id = $1",
                user_id,
            )
        if not row:
            return True  # Default is all enabled

        prefs = row["notification_preferences"]
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except (json.JSONDecodeError, TypeError):
                return True

        if isinstance(prefs, dict):
            return prefs.get(category, True)

        return True

    except Exception as exc:
        logger.debug("Preference check failed, defaulting to allow: %s", exc)
        return True
