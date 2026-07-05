"""
AI chat service — manages AI sessions, messages, and context snapshots.

Phase 0: stores/retrieves data only. No real LLM calls.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.postgres import get_pg_pool
from backend.models.ai.tour import TourPlan

logger = logging.getLogger("ai_service.persistence.chat_store")


async def create_session(
    user_id: str,
    mode: str = "ask",
    title: Optional[str] = None,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    exchange: str = "binance",
) -> Optional[dict]:
    """Create a new AI chat session."""
    pool = await get_pg_pool()
    if pool is None:
        return None

    now = datetime.now(timezone.utc)
    uid = uuid.UUID(user_id)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ai_chat_sessions (user_id, title, mode, symbol, timeframe, exchange, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
            RETURNING id, user_id, title, mode, symbol, timeframe, exchange, status, created_at, updated_at
            """,
            uid, title, mode, symbol, timeframe, exchange, now,
        )

    return _session_to_dict(row) if row else None


async def get_sessions(user_id: str, limit: int = 20) -> List[dict]:
    """Get user's AI chat sessions."""
    pool = await get_pg_pool()
    if pool is None:
        return []

    uid = uuid.UUID(user_id)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.*, (SELECT COUNT(*) FROM ai_messages m WHERE m.session_id = s.id) AS message_count
            FROM ai_chat_sessions s
            WHERE s.user_id = $1 AND s.status != 'deleted'
            ORDER BY s.updated_at DESC
            LIMIT $2
            """,
            uid, limit,
        )

    return [_session_to_dict(row) for row in rows]


async def get_session_messages(
    session_id: str, user_id: str, limit: int = 100
) -> Optional[List[dict]]:
    """
    Get messages for a session. Verifies user ownership.

    Returns:
        List of message dicts, or None if session not found or unauthorized.
    """
    pool = await get_pg_pool()
    if pool is None:
        return None

    sid = uuid.UUID(session_id) if session_id else None
    if sid is None:
        logger.error("get_session_messages called with null/empty session_id")
        return None
    uid = uuid.UUID(user_id)

    async with pool.acquire() as conn:
        # Verify ownership
        owner = await conn.fetchval(
            "SELECT user_id FROM ai_chat_sessions WHERE id = $1", sid
        )
        if owner is None or owner != uid:
            return None

        rows = await conn.fetch(
            """
            SELECT id, session_id, role, content, model_provider, model_name,
                   token_input, token_output, latency_ms, created_at, metadata
            FROM ai_messages
            WHERE session_id = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            sid, limit,
        )

    return [_message_to_dict(row) for row in rows]


async def store_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
    token_input: Optional[int] = None,
    token_output: Optional[int] = None,
    latency_ms: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    """Store a chat message and return it."""
    pool = await get_pg_pool()
    if pool is None:
        return None

    try:
        sid = uuid.UUID(session_id) if session_id else None
    except ValueError:
        logger.error("store_message called with invalid session_id: %s", session_id)
        return None
    if sid is None:
        logger.error("store_message called with null/empty session_id")
        return None
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        logger.error("store_message called with invalid user_id: %s", user_id)
        return None
    now = datetime.now(timezone.utc)
    meta_json = json.dumps(metadata or {})

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ai_messages (session_id, user_id, role, content, model_provider,
                                     model_name, token_input, token_output, latency_ms,
                                     created_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
            RETURNING id, session_id, role, content, model_provider, model_name, created_at, metadata
            """,
            sid, uid, role, content, model_provider, model_name,
            token_input, token_output, latency_ms, now, meta_json,
        )

        # Update session updated_at
        await conn.execute(
            "UPDATE ai_chat_sessions SET updated_at = $1 WHERE id = $2",
            now, sid,
        )

    return _message_to_dict(row) if row else None


async def soft_delete_session(
    session_id: str,
    user_id: str,
) -> bool:
    """Soft-delete an AI chat session by setting status='deleted'.

    Verifies ownership first; returns False if the session does not
    exist or belongs to a different user.
    """
    pool = await get_pg_pool()
    if pool is None:
        return False

    try:
        sid = uuid.UUID(session_id) if session_id else None
        if sid is None:
            logger.error("delete_session called with null/empty session_id")
            return False
        uid = uuid.UUID(user_id)
    except ValueError:
        return False

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE ai_chat_sessions
            SET status = 'deleted', updated_at = now()
            WHERE id = $1 AND user_id = $2
            RETURNING id
            """,
            sid, uid,
        )
    return row is not None


async def store_chart_snapshot(
    user_id: str,
    session_id: Optional[str],
    context: dict,
) -> Optional[str]:
    """Store a chart context snapshot. Returns snapshot ID."""
    pool = await get_pg_pool()
    if pool is None:
        return None

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        logger.error("store_chart_snapshot called with invalid user_id: %s", user_id)
        return None
    try:
        sid = uuid.UUID(session_id) if session_id else None
    except ValueError:
        sid = None
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        snapshot_id = await conn.fetchval(
            """
            INSERT INTO ai_chart_snapshots (
                user_id, session_id, symbol, timeframe, exchange, chart_type,
                selected_indicators, active_drawings, latest_candle,
                market_context, data_freshness, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb, $10::jsonb, $11::jsonb, $12)
            RETURNING id
            """,
            uid, sid,
            context.get("symbol", "BTCUSDT"),
            context.get("timeframe", "1m"),
            context.get("exchange", "binance"),
            context.get("chart_type", "candles"),
            json.dumps(context.get("selected_indicators", [])),
            json.dumps(context.get("active_drawings", [])),
            json.dumps(context.get("latest_candle")),
            json.dumps(context.get("market_context", {})),
            json.dumps(context.get("data_freshness", {})),
            now,
        )

    return str(snapshot_id) if snapshot_id else None


async def update_session_metadata(
    session_id: str,
    user_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """Update session metadata (merged into existing context_summary).

    Merges the provided metadata into the session's ``context_summary``
    JSONB column. If ``context_summary`` doesn't exist yet, creates it.
    """
    pool = await get_pg_pool()
    if pool is None:
        return False

    try:
        sid = uuid.UUID(session_id) if session_id else None
        if sid is None:
            return False
        uid = uuid.UUID(user_id)
    except ValueError:
        return False

    now = datetime.now(timezone.utc)

    try:
        async with pool.acquire() as conn:
            import json as _json
            # Use COALESCE to handle NULL context_summary (sessions created before migration 002)
            result = await conn.execute(
                """
                UPDATE ai_chat_sessions
                SET context_summary = COALESCE(context_summary, '{}'::jsonb) || $1::jsonb,
                    updated_at = $2
                WHERE id = $3 AND user_id = $4
                """,
                _json.dumps(metadata), now, sid, uid,
            )
            return result and result != "UPDATE 0"
    except Exception as exc:
        logger.warning("update_session_metadata failed: %s", exc)
        return False


async def get_session_metadata(
    session_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """Get session metadata from ``context_summary`` column.

    Returns None if not found or unauthorized.
    """
    pool = await get_pg_pool()
    if pool is None:
        return None

    try:
        sid = uuid.UUID(session_id) if session_id else None
        if sid is None:
            return None
        uid = uuid.UUID(user_id)
    except ValueError:
        return None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT context_summary FROM ai_chat_sessions
            WHERE id = $1 AND user_id = $2
            """,
            sid, uid,
        )

    if row is None:
        return None

    meta = row.get("context_summary")
    if isinstance(meta, str):
        import json as _json
        meta = _json.loads(meta)
    return meta or {}


def _session_to_dict(row) -> dict:
    """Convert asyncpg Record to session dict."""
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "title": row.get("title"),
        "mode": row["mode"],
        "symbol": row.get("symbol"),
        "timeframe": row.get("timeframe"),
        "exchange": row.get("exchange"),
        "status": row["status"],
        "message_count": row.get("message_count", 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _message_to_dict(row) -> dict:
    """Convert asyncpg Record to message dict."""
    meta = row.get("metadata", {})
    if isinstance(meta, str):
        meta = json.loads(meta)

    is_mock = False
    tour_plan = None
    if isinstance(meta, dict):
        is_mock = meta.get("is_mock", False)
        # Surface the tour plan from metadata so reloads can offer
        # Replay without re-running the LLM. The plan is stored under
        # ``metadata.tour_plan`` by the orchestrator.
        stored_plan = meta.get("tour_plan")
        if isinstance(stored_plan, dict) and stored_plan:
            try:
                # Validate + coerce to TourPlan schema. ``steps`` may be
                # a list of dicts; Pydantic will coerce as needed.
                tour_plan = TourPlan.model_validate(stored_plan).model_dump(mode="json")
            except Exception:
                tour_plan = stored_plan

    return {
        "id": str(row["id"]),
        "session_id": str(row["session_id"]),
        "role": row["role"],
        "content": row["content"],
        "provider": row.get("model_provider"),
        "model_name": row.get("model_name"),
        "is_mock": is_mock,
        "token_input": row.get("token_input"),
        "token_output": row.get("token_output"),
        "latency_ms": row.get("latency_ms"),
        "created_at": row["created_at"],
        "metadata": meta,
        "tour_plan": tour_plan,
    }
