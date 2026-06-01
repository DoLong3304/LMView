"""
AI action service — validates and records proposed chart actions.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.postgres import get_pg_pool
from backend.models.ai import AIChartAction, AIChartActionType

logger = logging.getLogger("backend.services.ai_action_service")

# Known indicator names that the platform supports
KNOWN_INDICATORS = {
    "sma", "sma20", "sma50", "sma200",
    "ema", "ema12", "ema26", "ema50",
    "rsi", "rsi14",
    "macd",
    "bollinger", "bollinger_bands", "bb",
    "vwap",
    "atr", "atr14",
    "volume_ma",
    "stochastic",
    "ichimoku",
    "supertrend",
    "parabolic_sar", "psar",
    "mfi",
}

# Valid symbol pattern
SYMBOL_RE = re.compile(r"^[A-Z0-9]{1,20}$")

# Valid timeframes
VALID_TIMEFRAMES = {"1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"}

# Max payload size (characters)
MAX_PAYLOAD_SIZE = 10_000

# Dangerous content patterns
DANGEROUS_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"import\s+os", re.IGNORECASE),
    re.compile(r"subprocess", re.IGNORECASE),
    re.compile(r"__import__", re.IGNORECASE),
    re.compile(r"SELECT\s+.*\s+FROM", re.IGNORECASE),
    re.compile(r"DROP\s+TABLE", re.IGNORECASE),
    re.compile(r"document\.", re.IGNORECASE),
    re.compile(r"window\.", re.IGNORECASE),
    re.compile(r"\.innerHTML", re.IGNORECASE),
    re.compile(r"querySelector", re.IGNORECASE),
]


def validate_actions(actions: List[AIChartAction]) -> Dict[str, Any]:
    """
    Validate a list of proposed chart actions.

    Returns:
        Dict with valid, errors, warnings, and validated_actions.
    """
    if not actions:
        return {"valid": False, "errors": ["No actions provided"], "warnings": [], "validated_actions": []}

    errors: List[str] = []
    warnings: List[str] = []
    validated: List[AIChartAction] = []

    for i, action in enumerate(actions):
        action_errors = _validate_single_action(action, i)
        if action_errors:
            errors.extend(action_errors)
        else:
            validated.append(action)

    # Check total payload size
    payload_str = json.dumps([a.model_dump() for a in actions])
    if len(payload_str) > MAX_PAYLOAD_SIZE:
        errors.append(f"Total payload exceeds {MAX_PAYLOAD_SIZE} characters")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "validated_actions": validated,
    }


def _validate_single_action(action: AIChartAction, index: int) -> List[str]:
    """Validate a single chart action."""
    errors: List[str] = []
    prefix = f"Action[{index}]"
    params = action.params

    # Check for dangerous content in all string values
    _check_payload_safety(params, prefix, errors)

    # Validate action-specific params
    action_type = action.action_type

    if action_type == AIChartActionType.ADD_INDICATOR:
        indicator_name = params.get("indicator", "").lower()
        if not indicator_name:
            errors.append(f"{prefix}: 'indicator' parameter required")
        elif indicator_name not in KNOWN_INDICATORS:
            errors.append(f"{prefix}: Unknown indicator '{indicator_name}'")

    elif action_type == AIChartActionType.REMOVE_INDICATOR:
        indicator_name = params.get("indicator", "").lower()
        if not indicator_name:
            errors.append(f"{prefix}: 'indicator' parameter required")

    elif action_type == AIChartActionType.SET_VISIBLE_RANGE:
        start = params.get("start")
        end = params.get("end")
        if start is not None and end is not None:
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                errors.append(f"{prefix}: 'start' and 'end' must be numeric timestamps")
            elif start >= end:
                errors.append(f"{prefix}: 'start' must be before 'end'")

    elif action_type == AIChartActionType.HIGHLIGHT_REGION:
        price_top = params.get("price_top")
        price_bottom = params.get("price_bottom")
        if price_top is not None and price_bottom is not None:
            if not isinstance(price_top, (int, float)) or not isinstance(price_bottom, (int, float)):
                errors.append(f"{prefix}: 'price_top' and 'price_bottom' must be numeric")
            elif price_top <= price_bottom:
                errors.append(f"{prefix}: 'price_top' must be greater than 'price_bottom'")

        time_start = params.get("time_start")
        time_end = params.get("time_end")
        if time_start is not None and time_end is not None:
            if not isinstance(time_start, (int, float)) or not isinstance(time_end, (int, float)):
                errors.append(f"{prefix}: time range values must be numeric")
            elif time_start >= time_end:
                errors.append(f"{prefix}: 'time_start' must be before 'time_end'")

    elif action_type == AIChartActionType.DRAW_TRENDLINE:
        for point_key in ("start_point", "end_point"):
            point = params.get(point_key)
            if point and isinstance(point, dict):
                if "time" not in point or "price" not in point:
                    errors.append(f"{prefix}: '{point_key}' must have 'time' and 'price'")

    elif action_type == AIChartActionType.ADD_NOTE:
        text = params.get("text", "")
        if not text:
            errors.append(f"{prefix}: 'text' parameter required for add_note")
        elif len(text) > 500:
            errors.append(f"{prefix}: note text exceeds 500 characters")

    return errors


def _check_payload_safety(
    obj: Any, prefix: str, errors: List[str], depth: int = 0
) -> None:
    """Recursively check for dangerous content in action payloads."""
    if depth > 10:
        errors.append(f"{prefix}: Payload nesting too deep")
        return

    if isinstance(obj, str):
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(obj):
                errors.append(
                    f"{prefix}: Payload contains forbidden content "
                    f"(matched: {pattern.pattern})"
                )
                return
    elif isinstance(obj, dict):
        for key, value in obj.items():
            _check_payload_safety(value, f"{prefix}.{key}", errors, depth + 1)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_payload_safety(item, f"{prefix}[{i}]", errors, depth + 1)


async def record_action(
    user_id: str,
    session_id: Optional[str],
    message_id: Optional[str],
    action_type: str,
    action_payload: dict,
    validation_status: str = "valid",
    approval_status: str = "not_required",
    execution_status: str = "not_executed",
    reason: Optional[str] = None,
) -> Optional[str]:
    """Record a chart action in the database. Returns action ID."""
    pool = await get_pg_pool()
    if pool is None:
        return None

    uid = uuid.UUID(user_id)
    sid = uuid.UUID(session_id) if session_id else None
    mid = uuid.UUID(message_id) if message_id else None
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        action_id = await conn.fetchval(
            """
            INSERT INTO ai_tool_actions (
                user_id, session_id, message_id, action_type, action_payload,
                validation_status, approval_status, execution_status, reason, created_at
            )
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10)
            RETURNING id
            """,
            uid, sid, mid, action_type,
            json.dumps(action_payload),
            validation_status, approval_status, execution_status,
            reason, now,
        )

    return str(action_id) if action_id else None
