"""Chart Interaction Expert — proposes typed, validated chart actions.

Generates tool-call proposals for chart interactions in Interact mode.
Every action maps to a typed, validated tool definition. Never executes
arbitrary code.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from ai_service.agents.base_expert import BaseExpert
from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput

logger = logging.getLogger("ai_service.agents.experts.chart_interaction")

# ── Typed Tool Definitions ────────────────────────────────────────────────────
# Every frontend action must map to one of these. No arbitrary code execution.

CHART_TOOLS: Dict[str, Dict[str, Any]] = {
    "set_visible_range": {
        "description": "Set the visible time range on the chart",
        "parameters": {
            "from_timestamp": {"type": "integer", "description": "Start time (epoch ms)"},
            "to_timestamp": {"type": "integer", "description": "End time (epoch ms)"},
        },
        "required": ["from_timestamp", "to_timestamp"],
    },
    "add_indicator": {
        "description": "Add a technical indicator to the chart",
        "parameters": {
            "indicator_name": {
                "type": "string",
                "enum": [
                    "sma20", "sma50", "ema12", "ema26", "rsi", "macd",
                    "bollinger_bands", "vwap", "atr", "volume_ma",
                    "stochastic", "mfi", "ichimoku", "supertrend", "psar",
                ],
            },
            "params": {"type": "object", "description": "Indicator-specific parameters"},
        },
        "required": ["indicator_name"],
    },
    "remove_indicator": {
        "description": "Remove a technical indicator from the chart",
        "parameters": {
            "indicator_name": {"type": "string"},
        },
        "required": ["indicator_name"],
    },
    "draw_trendline": {
        "description": "Draw a trendline between two points",
        "parameters": {
            "from_time": {"type": "integer", "description": "Start time (epoch ms)"},
            "from_price": {"type": "number", "description": "Start price"},
            "to_time": {"type": "integer", "description": "End time (epoch ms)"},
            "to_price": {"type": "number", "description": "End price"},
            "color": {"type": "string", "description": "CSS color"},
            "style": {"type": "string", "enum": ["solid", "dashed", "dotted"]},
        },
        "required": ["from_time", "from_price", "to_time", "to_price"],
    },
    "highlight_region": {
        "description": "Highlight a time/price region on the chart",
        "parameters": {
            "from_time": {"type": "integer"},
            "to_time": {"type": "integer"},
            "from_price": {"type": "number"},
            "to_price": {"type": "number"},
            "color": {"type": "string"},
            "label": {"type": "string"},
        },
        "required": ["from_time", "to_time"],
    },
    "create_annotation": {
        "description": "Add a text annotation at a specific chart point",
        "parameters": {
            "time": {"type": "integer", "description": "Timestamp (epoch ms)"},
            "price": {"type": "number"},
            "text": {"type": "string", "maxLength": 200},
        },
        "required": ["time", "text"],
    },
    "set_timeframe": {
        "description": "Switch the chart timeframe",
        "parameters": {
            "timeframe": {
                "type": "string",
                "enum": ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"],
            },
        },
        "required": ["timeframe"],
    },
    "set_chart_type": {
        "description": "Change the chart type",
        "parameters": {
            "chart_type": {
                "type": "string",
                "enum": ["candles", "bars", "line", "area", "heikinAshi", "renko"],
            },
        },
        "required": ["chart_type"],
    },
    "highlight_section": {
        "description": "Highlight a UI section for user guidance",
        "parameters": {
            "section_id": {"type": "string"},
            "message": {"type": "string", "maxLength": 200},
        },
        "required": ["section_id"],
    },
}


class ChartInteractionExpert(BaseExpert):
    """Proposes validated chart actions from user requests."""

    name = "chart_interaction"

    async def execute(self, state: AgentState) -> ExpertOutput:
        """Propose chart actions based on user intent."""
        user_query = state.get("user_query", "")
        chart_context = state.get("chart_context")
        mode = state.get("mode", "ask")

        proposed_actions: List[Dict[str, Any]] = []
        warnings: List[str] = []
        data_sources: List[str] = ["chart_tool_definitions"]

        if mode != "interact":
            return ExpertOutput(
                expert_name=self.name,
                content="Chart interaction is available in Interact mode.",
                structured_data={"proposed_actions": [], "available_tools": list(CHART_TOOLS.keys())},
                confidence=0.3,
                data_sources=data_sources,
                warnings=["Chart actions only proposed in Interact mode."],
            )

        # Parse user intent for chart actions
        proposed_actions = _propose_actions(user_query, chart_context)

        # Validate all proposed actions
        valid_actions = []
        for action in proposed_actions:
            validation = _validate_action(action)
            if validation["valid"]:
                valid_actions.append(action)
            else:
                warnings.extend(validation["errors"])

        structured = {
            "proposed_actions": valid_actions,
            "rejected_count": len(proposed_actions) - len(valid_actions),
            "available_tools": list(CHART_TOOLS.keys()),
        }

        content = f"Proposed {len(valid_actions)} chart action(s)."
        if valid_actions:
            action_names = [a.get("tool") for a in valid_actions]
            content += f" Actions: {', '.join(action_names)}"

        confidence = 0.7 if valid_actions else 0.3

        return ExpertOutput(
            expert_name=self.name,
            content=content,
            structured_data=structured,
            confidence=confidence,
            data_sources=data_sources,
            warnings=warnings,
        )


def _propose_actions(
    query: str,
    chart_context: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Propose chart actions from user query using pattern matching.

    This is the rule-based path. When the synthesis node makes the LLM
    call, it can also produce tool calls which are validated here.
    """
    query_lower = query.lower()
    actions: List[Dict[str, Any]] = []

    # Indicator addition
    indicator_patterns = {
        r"\badd\b.*\brsi\b": "rsi",
        r"\badd\b.*\bmacd\b": "macd",
        r"\badd\b.*\bsma\b": "sma20",
        r"\badd\b.*\bema\b": "ema12",
        r"\badd\b.*\bbollinger\b": "bollinger_bands",
        r"\badd\b.*\bvwap\b": "vwap",
        r"\badd\b.*\bvolume\b": "volume_ma",
        r"\bshow\b.*\brsi\b": "rsi",
        r"\bshow\b.*\bmacd\b": "macd",
    }
    for pattern, indicator in indicator_patterns.items():
        if re.search(pattern, query_lower):
            actions.append({
                "tool": "add_indicator",
                "params": {"indicator_name": indicator},
            })

    # Timeframe switch
    tf_match = re.search(r"\bswitch\b.*?\b(1s|1m|5m|15m|1h|4h|1d|1w)\b", query_lower)
    if not tf_match:
        tf_match = re.search(r"\b(1s|1m|5m|15m|1h|4h|1d|1w)\b.*?\btimeframe\b", query_lower)
    if tf_match:
        actions.append({
            "tool": "set_timeframe",
            "params": {"timeframe": tf_match.group(1)},
        })

    # Chart type change
    chart_type_patterns = {
        r"\bcandle": "candles",
        r"\bbar\b": "bars",
        r"\bline\s*(chart)?": "line",
        r"\barea\b": "area",
        r"\bheikin": "heikinAshi",
    }
    for pattern, chart_type in chart_type_patterns.items():
        if re.search(pattern, query_lower) and re.search(r"\bchange|switch|set|use\b", query_lower):
            actions.append({
                "tool": "set_chart_type",
                "params": {"chart_type": chart_type},
            })
            break

    return actions


def _validate_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a proposed action against the tool definitions.

    Security: Only tools in CHART_TOOLS are allowed. No arbitrary code.
    """
    tool_name = action.get("tool", "")
    params = action.get("params", {})

    if tool_name not in CHART_TOOLS:
        return {
            "valid": False,
            "errors": [f"Unknown tool: {tool_name}. Only {list(CHART_TOOLS.keys())} are allowed."],
        }

    tool_def = CHART_TOOLS[tool_name]
    required = tool_def.get("required", [])
    errors: List[str] = []

    for req_param in required:
        if req_param not in params:
            errors.append(f"Missing required parameter '{req_param}' for tool '{tool_name}'.")

    # Validate enum values
    for param_name, param_val in params.items():
        param_def = tool_def.get("parameters", {}).get(param_name, {})
        allowed_values = param_def.get("enum")
        if allowed_values and param_val not in allowed_values:
            errors.append(
                f"Invalid value '{param_val}' for '{param_name}' in '{tool_name}'. "
                f"Allowed: {allowed_values}"
            )

    return {"valid": len(errors) == 0, "errors": errors}


def get_tool_catalog() -> Dict[str, Dict[str, Any]]:
    """Return the full tool catalog for API/debug endpoints."""
    return CHART_TOOLS.copy()
