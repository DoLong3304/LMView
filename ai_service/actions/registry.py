"""Reusable AI action catalog.

Frontend and backend share these definitions for function calls, debug tester,
and compatibility chart-action validation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.models.ai.chart_actions import AIChartAction, AIChartActionType
from ai_service.actions.validator import KNOWN_INDICATORS, VALID_DRAWING_TOOLS

ACTION_CATALOG_VERSION = "2.0.0"


def _schema(
    name: str,
    description: str,
    properties: Dict[str, Any],
    required: List[str] | None = None,
    action_type: str | None = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "action_type": action_type or name,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


def get_action_catalog() -> Dict[str, Any]:
    """Return supported reusable function schemas."""
    indicators = sorted(KNOWN_INDICATORS)
    drawing_tools = sorted(VALID_DRAWING_TOOLS)
    functions = [
        _schema(
            "add_indicator",
            "Show a supported chart indicator.",
            {"indicator": {"type": "string", "enum": indicators}},
            ["indicator"],
            AIChartActionType.ADD_INDICATOR.value,
        ),
        _schema(
            "remove_indicator",
            "Hide a supported chart indicator.",
            {"indicator": {"type": "string", "enum": indicators}},
            ["indicator"],
            AIChartActionType.REMOVE_INDICATOR.value,
        ),
        _schema(
            "toggle_indicator",
            "Toggle a supported chart indicator.",
            {"indicator": {"type": "string", "enum": indicators}},
            ["indicator"],
            AIChartActionType.TOGGLE_INDICATOR.value,
        ),
        _schema(
            "draw_tool",
            "Select or place a drawing tool on the chart.",
            {
                "tool": {"type": "string", "enum": drawing_tools},
                "points": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Optional chart points with time/price.",
                },
            },
            ["tool"],
            AIChartActionType.DRAW_TOOL.value,
        ),
        _schema(
            "highlight_section",
            "Highlight a section of the LMView interface for guided help.",
            {
                "target": {"type": "string", "description": "Stable DOM selector or section key."},
                "label": {"type": "string"},
                "message": {"type": "string"},
            },
            ["target"],
            "highlight_section",
        ),
        _schema(
            "start_tour",
            "Start a user-paced LMView guided tour.",
            {
                "tour_id": {"type": "string", "default": "lmview-overview"},
                "start_step": {"type": "integer", "minimum": 0},
            },
            [],
            "start_tour",
        ),
        _schema(
            "clear_ai_annotations",
            "Clear AI-created highlights and annotations.",
            {},
            [],
            AIChartActionType.CLEAR_AI_ANNOTATIONS.value,
        ),
        _schema(
            "toggle_timeframe",
            "Switch chart timeframe.",
            {"timeframe": {"type": "string", "enum": ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"]}},
            ["timeframe"],
            AIChartActionType.TOGGLE_TIMEFRAME.value,
        ),
        _schema(
            "toggle_market",
            "Switch market symbol.",
            {"symbol": {"type": "string", "pattern": "^[A-Z0-9]{1,20}$"}},
            ["symbol"],
            AIChartActionType.TOGGLE_MARKET.value,
        ),
    ]
    return {"version": ACTION_CATALOG_VERSION, "functions": functions}


def propose_tool_calls(message: str, mode: str) -> List[Dict[str, Any]]:
    """Small deterministic action proposal for Interact and debug fallback."""
    if mode != "interact":
        return []

    text = message.lower()
    calls: List[Dict[str, Any]] = []

    if "tour" in text or "guide" in text or "tutorial" in text:
        calls.append({
            "name": "start_tour",
            "arguments": {"tour_id": "lmview-overview"},
            "reason": "User asked for a guided walkthrough.",
            "requires_approval": False,
        })

    for indicator in sorted(KNOWN_INDICATORS, key=len, reverse=True):
        compact = indicator.replace("_", " ")
        if re.search(rf"\b{re.escape(compact)}\b", text):
            action = "remove_indicator" if any(w in text for w in ("remove", "hide", "turn off")) else "add_indicator"
            calls.append({
                "name": action,
                "arguments": {"indicator": indicator},
                "reason": f"User referenced {indicator}.",
                "requires_approval": True,
            })
            break

    for tool in sorted(VALID_DRAWING_TOOLS, key=len, reverse=True):
        compact = tool.replace("_", " ").lower()
        if compact in text:
            calls.append({
                "name": "draw_tool",
                "arguments": {"tool": tool, "points": []},
                "reason": f"User referenced drawing tool {tool}.",
                "requires_approval": True,
            })
            break

    if "highlight" in text:
        calls.append({
            "name": "highlight_section",
            "arguments": {"target": "chart", "label": "Chart"},
            "reason": "User requested a highlight.",
            "requires_approval": False,
        })

    return calls


def tool_calls_to_chart_actions(tool_calls: List[Dict[str, Any]]) -> List[AIChartAction]:
    """Convert supported tool calls to legacy chart action DTOs."""
    by_name = {item["name"]: item for item in get_action_catalog()["functions"]}
    actions: List[AIChartAction] = []
    for call in tool_calls:
        name = call.get("name")
        definition = by_name.get(name)
        if not definition:
            continue
        action_type = definition.get("action_type")
        if action_type not in {item.value for item in AIChartActionType}:
            continue
        actions.append(
            AIChartAction(
                action_type=AIChartActionType(action_type),
                params=call.get("arguments") or {},
                reason=call.get("reason"),
                requires_approval=bool(call.get("requires_approval", True)),
            )
        )
    return actions
