"""
Tests for the notification creation service.
"""
import asyncio
import json
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.notification_service import (
    create_notification,
    create_notification_for_users,
    create_notification_for_all_admins,
    notify_ai_action_completed,
    notify_news_risk_event,
    notify_system_degraded,
    notify_alert_triggered,
    _check_user_preference,
    VALID_CATEGORIES,
    VALID_SEVERITIES,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_pool(fetchval_return=None, fetch_return=None, fetchrow_return=None):
    """Create a mock PostgreSQL pool."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=fetchval_return or uuid.uuid4())
    mock_conn.fetch = AsyncMock(return_value=fetch_return or [])
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=_AsyncCtxMgr(mock_conn))

    return mock_pool, mock_conn


class _AsyncCtxMgr:
    def __init__(self, conn):
        self._conn = conn
    async def __aenter__(self):
        return self._conn
    async def __aexit__(self, *args):
        pass


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestCreateNotification:
    def test_creates_notification_successfully(self):
        notification_id = uuid.uuid4()
        pool, conn = _mock_pool(fetchval_return=notification_id)

        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            result = _run(create_notification(
                user_id=str(uuid.uuid4()),
                category="system",
                title="Test notification",
                body="Test body",
                severity="info",
                respect_preferences=False,
            ))

        assert result == str(notification_id)
        conn.fetchval.assert_called_once()

    def test_returns_none_for_invalid_category(self):
        result = _run(create_notification(
            user_id=str(uuid.uuid4()),
            category="invalid_category",
            title="Test",
        ))
        assert result is None

    def test_returns_none_when_pool_unavailable(self):
        with patch("backend.services.notification_service.get_pg_pool", return_value=None):
            result = _run(create_notification(
                user_id=str(uuid.uuid4()),
                category="system",
                title="Test",
            ))
        assert result is None

    def test_defaults_severity_to_info(self):
        pool, conn = _mock_pool(fetchval_return=uuid.uuid4())

        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            _run(create_notification(
                user_id=str(uuid.uuid4()),
                category="alert",
                title="Test",
                severity="INVALID",
                respect_preferences=False,
            ))

        # Check that the call was made with "info" severity
        call_args = conn.fetchval.call_args
        assert call_args[0][3] == "info"  # severity param position

    def test_respects_preference_disabled(self):
        pool, conn = _mock_pool(
            fetchrow_return={"notification_preferences": json.dumps({"news": False})}
        )

        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            result = _run(create_notification(
                user_id=str(uuid.uuid4()),
                category="news",
                title="Suppressed",
                respect_preferences=True,
            ))

        assert result is None

    def test_allows_when_no_preferences_exist(self):
        notification_id = uuid.uuid4()
        pool, conn = _mock_pool(fetchval_return=notification_id, fetchrow_return=None)

        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            result = _run(create_notification(
                user_id=str(uuid.uuid4()),
                category="news",
                title="Allowed by default",
                respect_preferences=True,
            ))

        assert result == str(notification_id)


class TestCreateNotificationForUsers:
    def test_creates_for_multiple_users(self):
        pool, _ = _mock_pool(fetchval_return=uuid.uuid4())
        user_ids = [str(uuid.uuid4()) for _ in range(3)]

        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            count = _run(create_notification_for_users(
                user_ids=user_ids,
                category="system",
                title="Broadcast",
                respect_preferences=False,
            ))

        assert count == 3


class TestCreateNotificationForAllAdmins:
    def test_sends_to_all_admins(self):
        admin_ids = [uuid.uuid4(), uuid.uuid4()]
        pool, conn = _mock_pool(
            fetchval_return=uuid.uuid4(),
            fetch_return=[{"id": aid} for aid in admin_ids],
        )

        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            count = _run(create_notification_for_all_admins(
                category="system",
                title="Admin alert",
                severity="warning",
            ))

        assert count == 2

    def test_returns_zero_when_no_pool(self):
        with patch("backend.services.notification_service.get_pg_pool", return_value=None):
            count = _run(create_notification_for_all_admins(
                category="system",
                title="No pool",
            ))
        assert count == 0


class TestEventHelpers:
    def test_ai_action_completed_success(self):
        pool, _ = _mock_pool(fetchval_return=uuid.uuid4())
        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            result = _run(notify_ai_action_completed(
                user_id=str(uuid.uuid4()),
                action_type="add_indicator",
                success=True,
                details="RSI added",
            ))
        assert result is not None

    def test_ai_action_completed_failure(self):
        pool, _ = _mock_pool(fetchval_return=uuid.uuid4())
        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            result = _run(notify_ai_action_completed(
                user_id=str(uuid.uuid4()),
                action_type="remove_indicator",
                success=False,
                details="Indicator not found",
            ))
        assert result is not None

    def test_news_risk_event(self):
        pool, _ = _mock_pool(fetchval_return=uuid.uuid4())
        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            result = _run(notify_news_risk_event(
                user_id=str(uuid.uuid4()),
                symbol="BTC",
                headline="Exchange hacked",
                sentiment_label="negative",
                source="coindesk",
            ))
        assert result is not None

    def test_alert_triggered(self):
        pool, _ = _mock_pool(fetchval_return=uuid.uuid4())
        with patch("backend.services.notification_service.get_pg_pool", return_value=pool):
            result = _run(notify_alert_triggered(
                user_id=str(uuid.uuid4()),
                symbol="ETHUSDT",
                alert_type="price",
                alert_message="ETH crossed $5000",
                current_price=5001.5,
            ))
        assert result is not None


class TestCheckUserPreference:
    def test_returns_true_when_no_row(self):
        pool, _ = _mock_pool(fetchrow_return=None)
        result = _run(_check_user_preference(pool, uuid.uuid4(), "system"))
        assert result is True

    def test_returns_false_when_disabled(self):
        pool, _ = _mock_pool(
            fetchrow_return={"notification_preferences": json.dumps({"alerts": False})}
        )
        result = _run(_check_user_preference(pool, uuid.uuid4(), "alerts"))
        assert result is False

    def test_returns_true_when_enabled(self):
        pool, _ = _mock_pool(
            fetchrow_return={"notification_preferences": json.dumps({"alerts": True})}
        )
        result = _run(_check_user_preference(pool, uuid.uuid4(), "alerts"))
        assert result is True


class TestValidConstants:
    def test_valid_categories(self):
        assert "system" in VALID_CATEGORIES
        assert "alert" in VALID_CATEGORIES
        assert "news" in VALID_CATEGORIES
        assert "ai" in VALID_CATEGORIES

    def test_valid_severities(self):
        assert "info" in VALID_SEVERITIES
        assert "success" in VALID_SEVERITIES
        assert "warning" in VALID_SEVERITIES
        assert "error" in VALID_SEVERITIES
