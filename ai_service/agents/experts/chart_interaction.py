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
            "indicator": {
                "type": "string",
                "enum": [
                    "sma20", "sma50", "ema12", "ema26", "rsi", "macd",
                    "bollinger_bands", "vwap", "atr", "volume_ma",
                    "stochastic", "mfi", "ichimoku", "supertrend", "psar",
                ],
            },
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
        "required": [],  # Validated dynamically to allow either indicator or indicator_name
    },
    "remove_indicator": {
        "description": "Remove a technical indicator from the chart",
        "parameters": {
            "indicator": {"type": "string"},
            "indicator_name": {"type": "string"},
        },
        "required": [],
    },
    "toggle_indicator": {
        "description": "Toggle a technical indicator on the chart",
        "parameters": {
            "indicator": {"type": "string"},
            "indicator_name": {"type": "string"},
        },
        "required": [],
    },
    "draw_tool": {
        "description": "Select or place a drawing tool on the chart.",
        "parameters": {
            "tool": {"type": "string", "enum": ["trendline", "fibonacci", "rectangle", "cursor"]},
            "points": {"type": "array", "items": {"type": "object"}},
            "text": {"type": "string"},
        },
        "required": ["tool"],
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
    "highlight_chart_area": {
        "description": "Highlight a rectangular area inside the chart by percentages.",
        "parameters": {
            "left_pct": {"type": "number", "minimum": 0, "maximum": 100, "default": 20},
            "top_pct": {"type": "number", "minimum": 0, "maximum": 100, "default": 20},
            "width_pct": {"type": "number", "minimum": 1, "maximum": 100, "default": 40},
            "height_pct": {"type": "number", "minimum": 1, "maximum": 100, "default": 30},
            "label": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": [],
    },
    "highlight_candles": {
        "description": "Highlight candles by index range or timestamp range.",
        "parameters": {
            "from_index": {"type": "integer", "minimum": 0},
            "to_index": {"type": "integer", "minimum": 0},
            "start_time": {"type": "integer"},
            "end_time": {"type": "integer"},
            "label": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": [],
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
            "target": {"type": "string"},
            "section_id": {"type": "string"},
            "message": {"type": "string", "maxLength": 200},
        },
        "required": [],
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
            action_names = [a.get("action_type") or a.get("tool") for a in valid_actions]
            content += f" Actions: {', '.join(filter(None, action_names))}"

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
    """Propose chart actions from user query using pattern matching."""
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
                "action_type": "add_indicator",
                "tool": "add_indicator",
                "params": {"indicator": indicator, "indicator_name": indicator},
                "reason": f"Show indicator {indicator}.",
                "requires_approval": True,
            })

    # Timeframe switch
    tf_match = re.search(r"\bswitch\b.*?\b(1s|1m|5m|15m|1h|4h|1d|1w)\b", query_lower)
    if not tf_match:
        tf_match = re.search(r"\b(1s|1m|5m|15m|1h|4h|1d|1w)\b.*?\btimeframe\b", query_lower)
    if tf_match:
        timeframe = tf_match.group(1)
        actions.append({
            "action_type": "set_timeframe",
            "tool": "set_timeframe",
            "params": {"timeframe": timeframe},
            "reason": f"Switch chart timeframe to {timeframe}.",
            "requires_approval": True,
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
                "action_type": "set_chart_type",
                "tool": "set_chart_type",
                "params": {"chart_type": chart_type},
                "reason": f"Switch chart type to {chart_type}.",
                "requires_approval": True,
            })
            break

    return actions


def _validate_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a proposed action against the tool definitions.

    Security: Only tools in CHART_TOOLS are allowed. No arbitrary code.
    """
    tool_name = action.get("action_type") or action.get("tool") or ""
    params = action.get("params", {})

    if tool_name not in CHART_TOOLS:
        return {
            "valid": False,
            "errors": [f"Unknown tool: {tool_name}. Only {list(CHART_TOOLS.keys())} are allowed."],
        }

    tool_def = CHART_TOOLS[tool_name]
    required = tool_def.get("required", [])
    errors: List[str] = []

    # Map dynamic values to support both old and new keys
    normalized_params = {}
    for k, v in params.items():
        if k == "indicator_name":
            normalized_params["indicator"] = v
            normalized_params["indicator_name"] = v
        elif k == "section_id":
            normalized_params["target"] = v
            normalized_params["section_id"] = v
        else:
            normalized_params[k] = v

    # Inject default required parameters if missing but present in alternatives
    if tool_name in {"add_indicator", "remove_indicator", "toggle_indicator"}:
        if "indicator" not in normalized_params and "indicator_name" in normalized_params:
            normalized_params["indicator"] = normalized_params["indicator_name"]
        elif "indicator_name" not in normalized_params and "indicator" in normalized_params:
            normalized_params["indicator_name"] = normalized_params["indicator"]
        
        if not normalized_params.get("indicator"):
            errors.append(f"Missing required parameter 'indicator' for tool '{tool_name}'.")

    elif tool_name == "highlight_section":
        if "target" not in normalized_params and "section_id" in normalized_params:
            normalized_params["target"] = normalized_params["section_id"]
        elif "section_id" not in normalized_params and "target" in normalized_params:
            normalized_params["section_id"] = normalized_params["target"]
        
        if not normalized_params.get("target"):
            errors.append(f"Missing required parameter 'target' for tool 'highlight_section'.")
            
    else:
        for req_param in required:
            if req_param not in normalized_params:
                errors.append(f"Missing required parameter '{req_param}' for tool '{tool_name}'.")

    # Validate enum values
    for param_name, param_val in normalized_params.items():
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
