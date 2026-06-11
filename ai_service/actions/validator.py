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

logger = logging.getLogger("ai_service.actions.validator")

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
    "support_resistance", "support", "resistance",
    "whale_alert",
}

# Valid symbol pattern
SYMBOL_RE = re.compile(r"^[A-Z0-9]{1,20}$")

# Valid timeframes
VALID_TIMEFRAMES = {"1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"}

VALID_CHART_TYPES = {
    "candles", "bars", "line", "area", "heikinAshi", "renko",
    "lineBreak", "kagi", "pointFigure",
}

VALID_DRAWING_TOOLS = {
    "trendline", "ray", "extendedLine", "horizontal", "vertical",
    "rectangle", "arrow", "ellipse", "rotatedRectangle", "polyline",
    "fibRetracement", "fibExtension", "fibChannel", "fibArcs",
    "fibSpiral", "fibTimeZone", "text", "callout", "note", "balloon",
    "ruler", "priceRange", "dateRange", "riskReward", "elliottWave",
    "harmonicABCD", "horizontalRay", "parallelChannel", "pitchfork",
    "schiffPitchfork", "modifiedPitchfork", "insidePitchfork",
    "gannBox", "gannFan", "gannSquare", "cursor", "crosshair",
    "magnet", "lock", "hide", "eraser", "clearAll",
}

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

    if action_type in {
        AIChartActionType.ADD_INDICATOR,
        AIChartActionType.REMOVE_INDICATOR,
        AIChartActionType.TOGGLE_INDICATOR,
    }:
        indicator_name = params.get("indicator", "").lower()
        if not indicator_name:
            errors.append(f"{prefix}: 'indicator' parameter required")
        elif indicator_name not in KNOWN_INDICATORS:
            errors.append(f"{prefix}: Unknown indicator '{indicator_name}'")

    elif action_type == AIChartActionType.SET_VISIBLE_RANGE:
        start = params.get("start")
        end = params.get("end")
        if start is not None and end is not None:
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                errors.append(f"{prefix}: 'start' and 'end' must be numeric timestamps")
            elif start >= end:
                errors.append(f"{prefix}: 'start' must be before 'end'")

    elif action_type in {
        AIChartActionType.HIGHLIGHT_REGION,
        AIChartActionType.HIGHLIGHT_AREA,
    }:
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

    elif action_type == AIChartActionType.HIGHLIGHT_CANDLE:
        candle_time = params.get("time")
        has_index_range = isinstance(params.get("from_index"), int) and isinstance(params.get("to_index"), int)
        has_time_range = isinstance(params.get("start_time"), (int, float)) and isinstance(params.get("end_time"), (int, float))
        if not isinstance(candle_time, (int, float)) and not has_index_range and not has_time_range:
            errors.append(f"{prefix}: numeric 'time', index range, or time range required")

    elif action_type == AIChartActionType.HIGHLIGHT_INDICATOR:
        indicator_name = params.get("indicator", "").lower()
        if not indicator_name:
            errors.append(f"{prefix}: 'indicator' parameter required")
        elif indicator_name not in KNOWN_INDICATORS:
            errors.append(f"{prefix}: Unknown indicator '{indicator_name}'")
        if "point_index" in params and not isinstance(params["point_index"], int):
            errors.append(f"{prefix}: 'point_index' must be an integer")

    elif action_type == AIChartActionType.DRAW_TRENDLINE:
        for point_key in ("start_point", "end_point"):
            point = params.get(point_key)
            if point and isinstance(point, dict):
                if "time" not in point or "price" not in point:
                    errors.append(f"{prefix}: '{point_key}' must have 'time' and 'price'")
            else:
                errors.append(f"{prefix}: '{point_key}' parameter required")

    elif action_type == AIChartActionType.DRAW_TOOL:
        tool = params.get("tool")
        points = params.get("points")
        if tool not in VALID_DRAWING_TOOLS:
            errors.append(f"{prefix}: unsupported drawing tool")
        if points is not None and not isinstance(points, list):
            errors.append(f"{prefix}: 'points' must be an array when provided")
        elif isinstance(points, list):
            for point_index, point in enumerate(points):
                if not isinstance(point, dict) or "time" not in point or "price" not in point:
                    errors.append(f"{prefix}: points[{point_index}] must have 'time' and 'price'")

    elif action_type == AIChartActionType.TOGGLE_TIMEFRAME:
        timeframe = params.get("timeframe")
        if timeframe not in VALID_TIMEFRAMES:
            errors.append(f"{prefix}: valid 'timeframe' parameter required")

    elif action_type == AIChartActionType.TOGGLE_CHART:
        chart_type = params.get("chart_type")
        if chart_type not in VALID_CHART_TYPES:
            errors.append(f"{prefix}: valid 'chart_type' parameter required")

    elif action_type == AIChartActionType.TOGGLE_MARKET:
        symbol = str(params.get("symbol", "")).upper()
        if not symbol or not SYMBOL_RE.match(symbol):
            errors.append(f"{prefix}: valid 'symbol' parameter required")

    elif action_type == AIChartActionType.MOVE_RESIZE_CHART:
        if "direction" in params:
            if params.get("direction") not in {"in", "out"}:
                errors.append(f"{prefix}: zoom 'direction' must be in or out")
            return errors
        if "pane_id" not in params:
            errors.append(f"{prefix}: 'pane_id' parameter required")
        for key in ("x", "y", "width", "height"):
            if key in params and not isinstance(params[key], (int, float)):
                errors.append(f"{prefix}: '{key}' must be numeric")

    elif action_type == AIChartActionType.REPLAY_CHART:
        start_time = params.get("start_time")
        speed = params.get("speed", 1)
        if not isinstance(start_time, (int, float)):
            errors.append(f"{prefix}: numeric 'start_time' parameter required")
        if not isinstance(speed, (int, float)) or speed <= 0:
            errors.append(f"{prefix}: positive numeric 'speed' parameter required")

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
