"""Reusable AI action catalog.

Frontend and backend share these definitions for function calls, debug tester,
and compatibility chart-action validation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.models.ai.chart_actions import AIChartAction, AIChartActionType
from ai_service.actions.validator import KNOWN_INDICATORS, VALID_CHART_TYPES, VALID_DRAWING_TOOLS

ACTION_CATALOG_VERSION = "2.1.1"

SECTION_KEYS = [
    "app", "header", "chart", "chartToolbar", "chartCanvas", "drawingTools",
    "rightPanel", "rightPanelOverview", "watchlist", "watchlistList",
    "orderBook", "recentTrades", "marketsNews", "screener", "settings", "ai",
]
TIMEFRAMES = ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"]
HISTORICAL_TIMEFRAMES = [timeframe for timeframe in TIMEFRAMES if timeframe != "1s"]


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
                    "description": "Optional chart points like [{\"time\":1717200000,\"price\":67500}].",
                },
            },
            ["tool"],
            AIChartActionType.DRAW_TOOL.value,
        ),
        _schema(
            "highlight_section",
            "Highlight a section of the LMView interface for guided help.",
            {
                "target": {"type": "string", "enum": SECTION_KEYS},
                "label": {"type": "string"},
                "message": {"type": "string"},
                "include_chat": {"type": "boolean", "default": False},
            },
            ["target"],
            "highlight_section",
        ),
        _schema(
            "highlight_chart_area",
            "Highlight a rectangular area inside the chart by percentages.",
            {
                "left_pct": {"type": "number", "minimum": 0, "maximum": 100, "default": 20},
                "top_pct": {"type": "number", "minimum": 0, "maximum": 100, "default": 20},
                "width_pct": {"type": "number", "minimum": 1, "maximum": 100, "default": 40},
                "height_pct": {"type": "number", "minimum": 1, "maximum": 100, "default": 30},
                "label": {"type": "string"},
                "message": {"type": "string"},
            },
            [],
            AIChartActionType.HIGHLIGHT_AREA.value,
        ),
        _schema(
            "highlight_candles",
            "Highlight candles by index range or timestamp range.",
            {
                "from_index": {"type": "integer", "minimum": 0},
                "to_index": {"type": "integer", "minimum": 0},
                "start_time": {"type": "integer"},
                "end_time": {"type": "integer"},
                "label": {"type": "string"},
                "message": {"type": "string"},
            },
            [],
            AIChartActionType.HIGHLIGHT_CANDLE.value,
        ),
        _schema(
            "set_chart_type",
            "Switch chart type.",
            {"chart_type": {"type": "string", "enum": sorted(VALID_CHART_TYPES)}},
            ["chart_type"],
            AIChartActionType.TOGGLE_CHART.value,
        ),
        _schema(
            "set_timeframe",
            "Switch chart timeframe.",
            {"timeframe": {"type": "string", "enum": TIMEFRAMES}},
            ["timeframe"],
            AIChartActionType.TOGGLE_TIMEFRAME.value,
        ),
        _schema(
            "set_market",
            "Switch selected market symbol.",
            {"symbol": {"type": "string", "pattern": "^[A-Z0-9]{1,20}$"}},
            ["symbol"],
            AIChartActionType.TOGGLE_MARKET.value,
        ),
        _schema(
            "view_section",
            "Open and highlight a major LMView section.",
            {"target": {"type": "string", "enum": SECTION_KEYS}},
            ["target"],
            "view_section",
        ),
        _schema(
            "zoom_chart",
            "Zoom chart in or out.",
            {
                "direction": {"type": "string", "enum": ["in", "out"]},
                "anchor_ratio": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
            },
            ["direction"],
            AIChartActionType.MOVE_RESIZE_CHART.value,
        ),
        _schema(
            "scroll_chart",
            "Scroll chart horizontally.",
            {
                "target": {"type": "string", "enum": ["start", "end", "left", "right"]},
                "bars": {"type": "integer", "default": 20},
            },
            ["target"],
            AIChartActionType.SET_VISIBLE_RANGE.value,
        ),
        _schema(
            "fetch_historical_prices",
            "Fetch historical prices for the current or requested market. 1s is live-only.",
            {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string", "enum": HISTORICAL_TIMEFRAMES},
                "start_ms": {"type": "integer"},
                "end_ms": {"type": "integer"},
                "limit": {"type": "integer", "default": 100},
            },
            ["start_ms", "end_ms"],
            "fetch_historical_prices",
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
            {"timeframe": {"type": "string", "enum": TIMEFRAMES}},
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

    if any(term in text for term in ("tour", "guide", "tutorial", "demo", "learn how", "how to use", "show me around")):
        calls.append({
            "name": "start_tour",
            "arguments": {"tour_id": "lmview-overview"},
            "reason": "User asked for a guided walkthrough.",
            "requires_approval": False,
        })

    section_terms = {
        "overview": "rightPanelOverview",
        "watchlist": "watchlistList",
        "order book": "orderBook",
        "trades": "recentTrades",
        "recent trades": "recentTrades",
        "market": "marketsNews",
        "news": "marketsNews",
        "screener": "screener",
        "settings": "settings",
        "header": "header",
        "chart": "chart",
        "tools": "drawingTools",
    }
    if "show" in text or "view" in text or "open" in text or "highlight" in text:
        for term, target in section_terms.items():
            if term in text:
                calls.append({
                    "name": "view_section",
                    "arguments": {"target": target},
                    "reason": f"User referenced {term}.",
                    "requires_approval": False,
                })
                break

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

    for timeframe in TIMEFRAMES:
        if re.search(rf"\b{re.escape(timeframe)}\b", text):
            calls.append({
                "name": "set_timeframe",
                "arguments": {"timeframe": timeframe},
                "reason": f"User referenced timeframe {timeframe}.",
                "requires_approval": True,
            })
            break

    chart_types = sorted(VALID_CHART_TYPES, key=len, reverse=True)
    for chart_type in chart_types:
        phrase = chart_type.replace("_", " ").lower()
        if phrase.lower() in text:
            calls.append({
                "name": "set_chart_type",
                "arguments": {"chart_type": chart_type},
                "reason": f"User referenced chart type {chart_type}.",
                "requires_approval": True,
            })
            break

    match = re.search(r"\b([A-Z]{2,12}USDT)\b", message.upper())
    if match:
        calls.append({
            "name": "set_market",
            "arguments": {"symbol": match.group(1)},
            "reason": "User referenced a market symbol.",
            "requires_approval": True,
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
