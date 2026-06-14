"""Action executor — validates and audits chart actions before frontend execution.

Every chart action passes through this executor, which:
1. Validates against the typed tool definitions (allowlist-only).
2. Creates an audit record in PostgreSQL.
3. Returns a validated action proposal for user approval.

Security: No arbitrary JavaScript, SQL, or shell commands are ever executed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai_service.agents.experts.chart_interaction import CHART_TOOLS, _validate_action

logger = logging.getLogger("ai_service.actions.executor")


async def validate_and_audit_actions(
    proposed_actions: List[Dict[str, Any]],
    session_id: str,
    user_id: str,
    execution_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate proposed actions and create audit records.

    Args:
        proposed_actions: List of proposed actions from the chart expert.
        session_id: Current AI session ID.
        user_id: Authenticated user ID.
        execution_id: Agent execution ID for tracing.

    Returns:
        Dict with validated_actions, rejected_actions, and action_ids.
    """
    validated = []
    rejected = []
    action_ids = []

    for action in proposed_actions:
        action_id = str(uuid.uuid4())
        result = _validate_action(action)

        if result["valid"]:
            validated_action = {
                "action_id": action_id,
                "tool": action.get("tool"),
                "params": action.get("params", {}),
                "status": "pending_approval",
                "proposed_at": datetime.now(timezone.utc).isoformat(),
            }
            validated.append(validated_action)
            action_ids.append(action_id)
        else:
            rejected.append({
                "action_id": action_id,
                "tool": action.get("tool"),
                "errors": result["errors"],
                "status": "rejected",
            })

    # Store audit records
    await _store_action_audit(
        validated=validated,
        rejected=rejected,
        session_id=session_id,
        user_id=user_id,
        execution_id=execution_id,
    )

    return {
        "validated_actions": validated,
        "rejected_actions": rejected,
        "action_ids": action_ids,
        "total_proposed": len(proposed_actions),
        "total_validated": len(validated),
        "total_rejected": len(rejected),
    }


async def record_action_result(
    action_id: str,
    user_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    """Record the result of a user's action (approved/rejected/executed/undone).

    Args:
        action_id: The action ID from validation.
        user_id: Authenticated user who approved/rejected.
        status: "approved", "rejected", "executed", "undone", "failed".
        result: Optional result data from execution.
    """
    try:
        from backend.core.postgres import get_pg_pool
        pool = get_pg_pool()
        if not pool:
            return

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ai_chart_actions
                SET status = $1, result = $2::jsonb, updated_at = NOW()
                WHERE action_id = $3 AND user_id = $4::uuid
                """,
                status,
                _safe_json(result) if result else None,
                action_id,
                user_id,
            )
    except Exception as exc:
        logger.warning("Failed to record action result: %s", exc)


async def _store_action_audit(
    validated: List[Dict[str, Any]],
    rejected: List[Dict[str, Any]],
    session_id: str,
    user_id: str,
    execution_id: Optional[str] = None,
) -> None:
    """Store action audit records in PostgreSQL."""
    try:
        from backend.core.postgres import get_pg_pool
        pool = get_pg_pool()
        if not pool:
            return

        async with pool.acquire() as conn:
            for action in validated + rejected:
                await conn.execute(
                    """
                    INSERT INTO ai_chart_actions (
                        action_id, session_id, user_id, tool_name,
                        params, status, execution_id
                    ) VALUES ($1, $2::uuid, $3::uuid, $4, $5::jsonb, $6, $7)
                    ON CONFLICT DO NOTHING
                    """,
                    action["action_id"],
                    session_id,
                    user_id,
                    action.get("tool"),
                    _safe_json(action.get("params", {})),
                    action["status"],
                    execution_id,
                )
    except Exception as exc:
        logger.warning("Failed to store action audit: %s", exc)


def _safe_json(data: Any) -> Optional[str]:
    if data is None:
        return None
    try:
        import json
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return None
