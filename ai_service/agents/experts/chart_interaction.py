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
# Phase E: Comprehensive action catalog that mirrors the frontend handler
# registry. Any action added to the frontend handlerRegistry should also be
# defined here so the LLM can propose it.

CHART_TOOLS: Dict[str, Dict[str, Any]] = {
    # ── Chart configuration ────────────────────────────────────────────
    "set_timeframe": {
        "description": "Switch the chart timeframe for multi-timeframe analysis. Use this to zoom in/out: 1s/1m for detail, 4h/1d for broader trend.",
        "parameters": {
            "timeframe": {
                "type": "string",
                "enum": ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"],
            },
        },
        "required": ["timeframe"],
    },
    "set_chart_type": {
        "description": "Change the chart type for better visualization. heikinAshi smooths noise, renko ignores time, line shows trend clearly.",
        "parameters": {
            "chart_type": {
                "type": "string",
                "enum": ["candles", "bars", "line", "area", "heikinAshi", "renko"],
            },
        },
        "required": ["chart_type"],
    },
    "set_symbol": {
        "description": "Switch the selected market symbol (e.g., BTCUSDT, ETHUSDT, SOLUSDT). Used for cross-market analysis or when query involves a different symbol.",
        "parameters": {
            "symbol": {"type": "string", "description": "Trading pair symbol like BTCUSDT, ETHUSDT"},
        },
        "required": ["symbol"],
    },
    "set_visible_range": {
        "description": "Set the visible time range on the chart to zoom/pan to a specific time window.",
        "parameters": {
            "from_timestamp": {"type": "integer", "description": "Start time (epoch ms)"},
            "to_timestamp": {"type": "integer", "description": "End time (epoch ms)"},
        },
        "required": ["from_timestamp", "to_timestamp"],
    },

    # ── Indicators ─────────────────────────────────────────────────────
    "add_indicator": {
        "description": "Add a technical indicator to the chart. Used to display RSI, MACD, Bollinger Bands, etc.",
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
            "params": {"type": "object", "description": "Indicator-specific parameters like period"},
        },
        "required": [],
    },
    "remove_indicator": {
        "description": "Remove a technical indicator from the chart to declutter.",
        "parameters": {
            "indicator": {"type": "string"},
            "indicator_name": {"type": "string"},
        },
        "required": [],
    },
    "toggle_indicator": {
        "description": "Toggle a technical indicator on/off.",
        "parameters": {
            "indicator": {"type": "string"},
            "indicator_name": {"type": "string"},
        },
        "required": [],
    },
    "configure_indicator": {
        "description": "Update indicator parameters (period, colors, thresholds).",
        "parameters": {
            "indicator": {"type": "string", "description": "Indicator key"},
            "settings": {"type": "object", "description": "Settings to override (e.g. {period: 14, color: '#f00'})"},
        },
        "required": ["indicator", "settings"],
    },

    # ── Drawing tools ──────────────────────────────────────────────────
    "draw_tool": {
        "description": "Select or place a drawing tool on the chart. Supports all tools (trendline, fibonacci, rectangle, ellipse, channel, etc.). Use `points` array with {time, price} coordinates and optional `text` for labels.",
        "parameters": {
            "tool": {"type": "string", "enum": [
                "trendline", "fibonacci", "rectangle", "ellipse", "cursor",
                "horizontal", "vertical", "ray", "extendedLine",
                "parallelChannel", "disjointChannel",
                "fibRetracement", "fibExtension", "fibChannel",
                "gannBox", "gannFan",
                "pitchfork", "schiffPitchfork",
            ]},
            "points": {"type": "array", "items": {"type": "object"}, "description": "Array of {time: epoch_ms, price: number} coordinates"},
            "text": {"type": "string", "description": "Optional label/text for the drawing"},
            "color": {"type": "string", "description": "CSS color hex"},
            "lineWidth": {"type": "integer", "default": 2},
            "lineStyle": {"type": "string", "enum": ["solid", "dashed", "dotted"], "default": "solid"},
        },
        "required": ["tool"],
    },
    "draw_trendline": {
        "description": "Draw a trendline between two price/time points. Use for trend identification, channel lines.",
        "parameters": {
            "from_time": {"type": "integer", "description": "Start time (epoch ms)"},
            "from_price": {"type": "number", "description": "Start price"},
            "to_time": {"type": "integer", "description": "End time (epoch ms)"},
            "to_price": {"type": "number", "description": "End price"},
            "color": {"type": "string", "description": "CSS color hex"},
            "style": {"type": "string", "enum": ["solid", "dashed", "dotted"], "default": "solid"},
        },
        "required": ["from_time", "from_price", "to_time", "to_price"],
    },
    "create_annotation": {
        "description": "Add a text annotation at a specific chart point. Used to mark key levels, patterns, or notes.",
        "parameters": {
            "time": {"type": "integer", "description": "Timestamp (epoch ms)"},
            "price": {"type": "number", "description": "Price level for the annotation"},
            "text": {"type": "string", "maxLength": 200, "description": "Annotation text"},
            "color": {"type": "string", "description": "CSS color hex", "default": "#fbbf24"},
        },
        "required": ["time", "text"],
    },
    "clear_drawings": {
        "description": "Remove all AI-placed drawings from the chart. Use between walkthrough steps when keep_effects=false.",
        "parameters": {},
        "required": [],
    },
    "delete_drawing": {
        "description": "Delete a specific drawing by its id.",
        "parameters": {
            "drawing_id": {"type": "string"},
        },
        "required": ["drawing_id"],
    },
    "set_drawing_color": {
        "description": "Recolor an existing drawing.",
        "parameters": {
            "drawing_id": {"type": "string"},
            "color": {"type": "string", "description": "CSS color hex"},
        },
        "required": ["drawing_id", "color"],
    },

    # ── Highlight actions ──────────────────────────────────────────────
    "highlight_region": {
        "description": "Highlight a time/price region on the chart. Best for marking support/resistance zones, supply/demand areas.",
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
        "description": "Highlight a rectangular area inside the chart by percentages. More abstract than coordinates.",
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
        "description": "Highlight candles by index range or timestamp range. Use to point out specific candle patterns.",
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
    "highlight_contextual_zone": {
        "description": "Highlight a chart zone based on analysis context. Use when AI identifies a pattern, breakout, S/R test, or notable zone. Frontend maps zone_type + candle_count to actual chart coordinates.",
        "parameters": {
            "zone_type": {
                "type": "string",
                "enum": [
                    "breakout", "breakdown", "support_test", "resistance_test",
                    "bullish_divergence", "bearish_divergence", "consolidation",
                    "reversal_candles", "volume_spike", "trend_push",
                    "accumulation", "distribution", "recent_action",
                ],
            },
            "label": {"type": "string", "description": "Short label shown on the highlight"},
            "message": {"type": "string", "maxLength": 200, "description": "What to look for in this zone"},
            "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral"], "description": "Color bias for the highlight"},
            "candle_count": {"type": "integer", "minimum": 2, "maximum": 50, "default": 5},
        },
        "required": ["zone_type", "label"],
    },
    "highlight_section": {
        "description": "Highlight a UI section for user guidance (dim everything except target). Use to guide user attention to a specific panel.",
        "parameters": {
            "target": {"type": "string", "description": "Section name: chart, orderBook, watchlist, ai, overview, news, settings, etc."},
            "section_id": {"type": "string"},
            "message": {"type": "string", "maxLength": 200},
        },
        "required": [],
    },

    # ── Chart navigation ───────────────────────────────────────────────
    "zoom_chart": {
        "description": "Zoom chart in or out. Useful to get a broader view or focus on recent price action.",
        "parameters": {
            "direction": {"type": "string", "enum": ["in", "out"]},
            "anchor_ratio": {"type": "number", "default": 0.5, "description": "0=left edge, 1=right edge"},
        },
        "required": ["direction"],
    },
    "scroll_chart": {
        "description": "Scroll chart horizontally to see older data or return to live.",
        "parameters": {
            "target": {"type": "string", "enum": ["start", "end", "left", "right"]},
            "bars": {"type": "integer", "default": 20},
        },
        "required": ["target"],
    },
    "scroll_chart_to_time": {
        "description": "Scroll chart to a specific timestamp. Use to jump to a known event or pattern.",
        "parameters": {
            "time": {"type": "integer", "description": "Unix seconds or milliseconds"},
        },
        "required": ["time"],
    },
    "reset_chart_view": {
        "description": "Reset chart zoom and scroll to default (latest live candles).",
        "parameters": {},
        "required": [],
    },

    # ── Panel / view management ────────────────────────────────────────
    "open_panel": {
        "description": "Open a right-panel target (watchlist, order book, trades, AI helper).",
        "parameters": {
            "target": {"type": "string", "enum": ["ai", "overview", "watchlist", "orderBook", "recentTrades"]},
            "highlight": {"type": "boolean", "default": True},
        },
        "required": ["target"],
    },
    "close_panel": {
        "description": "Close the right panel.",
        "parameters": {},
        "required": [],
    },
    "switch_panel_tab": {
        "description": "Switch the right panel tab between watchlist, order book, or recent trades.",
        "parameters": {
            "tab": {"type": "string", "enum": ["watchlist", "orderBook", "recentTrades"]},
        },
        "required": ["tab"],
    },
    "switch_app_view": {
        "description": "Switch between main app views: charts, markets/news, or screener.",
        "parameters": {
            "view": {"type": "string", "enum": ["charts", "marketsNews", "screener"]},
        },
        "required": ["view"],
    },
    "view_section": {
        "description": "Open and highlight a major app section. Navigates to the section and dims everything else.",
        "parameters": {
            "target": {"type": "string", "description": "Section name"},
        },
        "required": ["target"],
    },
    "open_settings": {
        "description": "Open the settings modal.",
        "parameters": {},
        "required": [],
    },
    "close_settings": {
        "description": "Close the settings modal.",
        "parameters": {},
        "required": [],
    },

    # ── Historical data ────────────────────────────────────────────────
    "fetch_historical_prices": {
        "description": "Fetch historical candles for analysis. Returns OHLCV data for a symbol/timeframe range.",
        "parameters": {
            "symbol": {"type": "string", "default": "BTCUSDT"},
            "timeframe": {"type": "string", "enum": ["1m", "5m", "15m", "1h", "4h", "1d", "1w"], "default": "1h"},
            "start_ms": {"type": "integer"},
            "end_ms": {"type": "integer"},
            "limit": {"type": "integer", "default": 100},
        },
        "required": ["start_ms", "end_ms"],
    },

    # ── Walkthrough-specific actions ───────────────────────────────────
    "open_news_popup": {
        "description": "Open a draggable news article popup with the article URL. Use to show relevant news during analysis.",
        "parameters": {
            "url": {"type": "string", "description": "News article URL"},
            "title": {"type": "string", "description": "Display title"},
        },
        "required": ["url"],
    },
    "navigate_tab": {
        "description": "Navigate to a specific tab panel in the UI (chart, overview, watchlist, orderbook, trades, news, screener, ai, settings).",
        "parameters": {
            "tab": {"type": "string", "description": "Target tab name"},
        },
        "required": ["tab"],
    },
    "enter_replay": {
        "description": "Enter replay mode for a specific time range. Useful to demonstrate how price action evolved over a period.",
        "parameters": {
            "from_time": {"type": "integer", "description": "Start time (unix seconds)"},
            "to_time": {"type": "integer", "description": "End time (unix seconds)"},
        },
        "required": ["from_time", "to_time"],
    },
    "export_chart": {
        "description": "Export current chart view as PNG or CSV for saving or sharing.",
        "parameters": {
            "format": {"type": "string", "enum": ["png", "csv"], "default": "png"},
            "filename": {"type": "string"},
        },
        "required": [],
    },

    # ── Utility ────────────────────────────────────────────────────────
    "clear_ai_annotations": {
        "description": "Clear all AI highlights, action overlays, and tour annotations from the UI.",
        "parameters": {},
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
