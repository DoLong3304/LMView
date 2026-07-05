"""Tests for chart safety — tool validation, allowlist, and undo stack."""
from __future__ import annotations

import pytest
from ai_service.agents.experts.chart_interaction import (
    CHART_TOOLS,
    _validate_action,
    _propose_actions,
)
from ai_service.actions.undo import UndoStack, get_undo_stack, clear_session_undo
from ai_service.actions.tool_definitions import (
    get_tool_definitions,
    get_tool_names,
    is_valid_tool,
    format_tools_for_llm,
)


class TestToolValidation:
    def test_valid_add_indicator(self):
        result = _validate_action({"tool": "add_indicator", "params": {"indicator_name": "rsi"}})
        assert result["valid"] is True

    def test_invalid_tool_name(self):
        result = _validate_action({"tool": "execute_sql", "params": {}})
        assert result["valid"] is False
        assert "Unknown tool" in result["errors"][0]

    def test_invalid_enum_value(self):
        result = _validate_action({
            "tool": "add_indicator",
            "params": {"indicator_name": "invalid_indicator"},
        })
        assert result["valid"] is False

    def test_missing_required_param(self):
        result = _validate_action({"tool": "set_timeframe", "params": {}})
        assert result["valid"] is False
        assert "Missing required" in result["errors"][0]

    def test_valid_set_timeframe(self):
        result = _validate_action({"tool": "set_timeframe", "params": {"timeframe": "4h"}})
        assert result["valid"] is True

    def test_valid_draw_trendline(self):
        result = _validate_action({
            "tool": "draw_trendline",
            "params": {
                "from_time": 1000,
                "from_price": 65000,
                "to_time": 2000,
                "to_price": 66000,
            },
        })
        assert result["valid"] is True


class TestNoArbitraryExecution:
    """Ensure no arbitrary code execution is possible."""

    def test_no_shell_tool(self):
        assert "execute_shell" not in CHART_TOOLS
        assert "run_command" not in CHART_TOOLS

    def test_no_sql_tool(self):
        assert "execute_sql" not in CHART_TOOLS
        assert "run_query" not in CHART_TOOLS

    def test_no_javascript_tool(self):
        assert "execute_js" not in CHART_TOOLS
        assert "eval" not in CHART_TOOLS

    def test_all_tools_are_chart_related(self):
        chart_prefixes = {
            "set_", "add_", "remove_", "configure_", "draw_", "highlight_",
            "create_", "toggle_", "clear_", "delete_", "zoom_", "scroll_",
            "reset_", "open_", "close_", "switch_", "view_", "fetch_",
            "navigate_", "enter_", "export_",
        }
        for tool_name in CHART_TOOLS:
            assert any(tool_name.startswith(p) for p in chart_prefixes), \
                f"Tool '{tool_name}' doesn't match chart action prefixes"


class TestActionProposal:
    def test_add_rsi(self):
        actions = _propose_actions("add rsi to the chart", None)
        assert any(a["tool"] == "add_indicator" and a["params"]["indicator_name"] == "rsi" for a in actions)

    def test_switch_timeframe(self):
        actions = _propose_actions("switch to 15m timeframe", None)
        assert any(a["tool"] == "set_timeframe" and a["params"]["timeframe"] == "15m" for a in actions)

    def test_no_actions_from_unrelated_query(self):
        actions = _propose_actions("What is Bitcoin?", None)
        assert len(actions) == 0


class TestUndoStack:
    def test_push_and_pop(self):
        stack = UndoStack()
        entry = stack.push(
            action_id="a1",
            tool="add_indicator",
            params={"indicator_name": "rsi"},
        )
        assert entry.reverse_tool == "remove_indicator"
        assert stack.depth == 1

        popped = stack.pop()
        assert popped.action_id == "a1"
        assert stack.depth == 0

    def test_max_depth(self):
        stack = UndoStack(max_depth=3)
        for i in range(5):
            stack.push(
                action_id=f"a{i}",
                tool="add_indicator",
                params={"indicator_name": "rsi"},
            )
        assert stack.depth == 3

    def test_empty_pop(self):
        stack = UndoStack()
        assert stack.pop() is None

    def test_session_stacks(self):
        s1 = get_undo_stack("session-1")
        s2 = get_undo_stack("session-2")
        s1.push(action_id="a1", tool="add_indicator", params={"indicator_name": "rsi"})
        assert s1.depth == 1
        assert s2.depth == 0
        clear_session_undo("session-1")
        # After clear, a new stack is created
        s1_new = get_undo_stack("session-1")
        assert s1_new.depth == 0


class TestToolDefinitions:
    def test_get_definitions(self):
        defs = get_tool_definitions()
        assert "add_indicator" in defs
        assert "set_timeframe" in defs

    def test_get_names(self):
        names = get_tool_names()
        assert "add_indicator" in names
        assert len(names) >= 8

    def test_is_valid_tool(self):
        assert is_valid_tool("add_indicator") is True
        assert is_valid_tool("execute_sql") is False

    def test_format_for_llm(self):
        text = format_tools_for_llm()
        assert "add_indicator" in text
        assert "set_timeframe" in text
        assert "Parameters:" in text
