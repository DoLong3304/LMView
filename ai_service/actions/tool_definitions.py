"""Typed tool call definitions for Interact mode.

Canonical registry of all allowed chart actions. Every tool call proposed
by the AI must match one of these definitions. No arbitrary code execution.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai_service.agents.experts.chart_interaction import CHART_TOOLS


def get_tool_definitions() -> Dict[str, Dict[str, Any]]:
    """Return the complete tool definition catalog.

    This is the single source of truth for all allowed chart actions.
    The chart_interaction expert and the action executor both reference
    these definitions.
    """
    return CHART_TOOLS.copy()


def get_tool_names() -> List[str]:
    """Return all registered tool names."""
    return list(CHART_TOOLS.keys())


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """Get the JSON Schema for a specific tool.

    Returns empty dict if tool not found (invalid tool).
    """
    return CHART_TOOLS.get(tool_name, {})


def is_valid_tool(tool_name: str) -> bool:
    """Check if a tool name is in the allowlist."""
    return tool_name in CHART_TOOLS


def get_openai_tools() -> List[Dict[str, Any]]:
    """Convert CHART_TOOLS to OpenAI-compatible tools format.

    Returns a list of tool specs suitable for the ``tools`` parameter
    in OpenAI-compatible chat completion APIs (including DashScope/Qwen).
    Each tool has ``type: "function"`` and ``function`` with name, description,
    and parameters (JSON Schema).
    """
    openai_tools: List[Dict[str, Any]] = []
    for name, definition in CHART_TOOLS.items():
        desc = definition.get("description", "")
        params = definition.get("parameters", {})
        required = definition.get("required", [])

        # Build JSON Schema for parameters
        properties = {}
        for pname, pdef in params.items():
            prop = {}
            ptype = pdef.get("type", "string")
            # Map parameter type to JSON Schema type
            prop["type"] = ptype
            if pdef.get("description"):
                prop["description"] = pdef["description"]
            if pdef.get("enum"):
                prop["enum"] = pdef["enum"]
            if pdef.get("minimum") is not None:
                prop["minimum"] = pdef["minimum"]
            if pdef.get("maximum") is not None:
                prop["maximum"] = pdef["maximum"]
            if pdef.get("default") is not None:
                prop["default"] = pdef["default"]
            if pdef.get("maxLength") is not None:
                prop["maxLength"] = pdef["maxLength"]
            if pdef.get("items"):
                prop["items"] = pdef["items"]
            properties[pname] = prop

        schema: Dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required

        openai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": schema,
            },
        })

    return openai_tools


def format_tools_for_llm() -> str:
    """Format tool definitions as a string for LLM system prompts.

    Used by the synthesis node when in Interact mode to tell the LLM
    what tools are available.
    """
    parts = ["## Available Chart Tools"]
    for name, definition in CHART_TOOLS.items():
        desc = definition.get("description", "")
        params = definition.get("parameters", {})
        required = definition.get("required", [])

        parts.append(f"\n### {name}")
        parts.append(f"Description: {desc}")
        if params:
            parts.append("Parameters:")
            for pname, pdef in params.items():
                ptype = pdef.get("type", "any")
                pdesc = pdef.get("description", "")
                req = " (required)" if pname in required else ""
                enum_vals = pdef.get("enum")
                enum_str = f", values: {enum_vals}" if enum_vals else ""
                parts.append(f"  - {pname}: {ptype}{req} — {pdesc}{enum_str}")

    return "\n".join(parts)
