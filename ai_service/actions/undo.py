"""Undo stack management for chart actions.

Maintains a per-session undo history. Each executed action creates an
UndoEntry that can reverse the operation.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_service.actions.undo")

# Maximum undo entries per session
MAX_UNDO_DEPTH = 50


@dataclass
class UndoEntry:
    """Reversible record for a single chart action."""
    action_id: str
    tool: str
    params: Dict[str, Any] = field(default_factory=dict)
    reverse_tool: Optional[str] = None
    reverse_params: Optional[Dict[str, Any]] = None
    executed_at: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "tool": self.tool,
            "params": self.params,
            "reverse_tool": self.reverse_tool,
            "reverse_params": self.reverse_params,
            "executed_at": self.executed_at,
            "description": self.description,
        }


# ── Reverse action mappings ──────────────────────────────────────────────────

REVERSE_ACTIONS: Dict[str, str] = {
    "add_indicator": "remove_indicator",
    "draw_trendline": "remove_drawing",
    "highlight_region": "remove_highlight",
    "create_annotation": "remove_annotation",
    "set_timeframe": "set_timeframe",
    "set_chart_type": "set_chart_type",
    "set_visible_range": "set_visible_range",
}


class UndoStack:
    """Per-session undo stack for chart actions.

    Usage::

        stack = get_undo_stack(session_id)
        stack.push(action_id="123", tool="add_indicator",
                   params={"indicator_name": "rsi"})

        entry = stack.pop()
        # entry.reverse_tool = "remove_indicator"
        # entry.reverse_params = {"indicator_name": "rsi"}
    """

    def __init__(self, max_depth: int = MAX_UNDO_DEPTH):
        self._entries: List[UndoEntry] = []
        self._max_depth = max_depth

    def push(
        self,
        action_id: str,
        tool: str,
        params: Dict[str, Any],
        previous_state: Optional[Dict[str, Any]] = None,
    ) -> UndoEntry:
        """Push an executed action onto the undo stack.

        Args:
            action_id: Unique ID of the executed action.
            tool: Tool name that was executed.
            params: Parameters of the executed action.
            previous_state: State before the action for reversal.

        Returns:
            The created UndoEntry.
        """
        reverse_tool = REVERSE_ACTIONS.get(tool)
        reverse_params = _compute_reverse_params(tool, params, previous_state)

        entry = UndoEntry(
            action_id=action_id,
            tool=tool,
            params=params,
            reverse_tool=reverse_tool,
            reverse_params=reverse_params,
            executed_at=datetime.now(timezone.utc).isoformat(),
            description=f"Undo {tool}({params})",
        )

        self._entries.append(entry)

        # Enforce max depth
        if len(self._entries) > self._max_depth:
            self._entries = self._entries[-self._max_depth:]

        return entry

    def pop(self) -> Optional[UndoEntry]:
        """Pop the most recent action from the undo stack."""
        if not self._entries:
            return None
        return self._entries.pop()

    def peek(self) -> Optional[UndoEntry]:
        """Peek at the most recent action without removing it."""
        if not self._entries:
            return None
        return self._entries[-1]

    @property
    def entries(self) -> List[UndoEntry]:
        """All entries in the undo stack (oldest first)."""
        return list(self._entries)

    @property
    def depth(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        """Clear all undo entries."""
        self._entries.clear()


def _compute_reverse_params(
    tool: str,
    params: Dict[str, Any],
    previous_state: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Compute the parameters needed to reverse an action."""
    if tool == "add_indicator":
        return {"indicator_name": params.get("indicator_name")}

    if tool == "set_timeframe" and previous_state:
        return {"timeframe": previous_state.get("timeframe")}

    if tool == "set_chart_type" and previous_state:
        return {"chart_type": previous_state.get("chart_type")}

    if tool == "set_visible_range" and previous_state:
        return {
            "from_timestamp": previous_state.get("from_timestamp"),
            "to_timestamp": previous_state.get("to_timestamp"),
        }

    if tool in ("draw_trendline", "highlight_region", "create_annotation"):
        return {"id": params.get("id") or params.get("action_id")}

    return None


# ── Session-level undo stack management ──────────────────────────────────────

_session_stacks: Dict[str, UndoStack] = {}


def get_undo_stack(session_id: str) -> UndoStack:
    """Get or create the undo stack for a session."""
    if session_id not in _session_stacks:
        _session_stacks[session_id] = UndoStack()
    return _session_stacks[session_id]


def clear_session_undo(session_id: str) -> None:
    """Clear undo history for a session."""
    if session_id in _session_stacks:
        del _session_stacks[session_id]
