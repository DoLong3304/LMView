"""
Tour/Walkthrough Plan models for Interact mode guided analysis tours.

Each tour is a sequence of steps with multiple simultaneous actions,
accompanied by explanations that the user progresses through self-paced.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GuidedAction(BaseModel):
    """A single action within a tour step.

    Multiple actions can be grouped in one step (e.g., draw a trendline
    AND add RSI indicator simultaneously).
    """
    type: str = Field(
        ...,
        description="Action type: add_indicator, draw_tool, draw_trendline, set_timeframe, "
                    "highlight_section, highlight_candles, highlight_contextual_zone, "
                    "set_chart_type, scroll_to_time, navigate_tab, open_news_popup, "
                    "set_symbol, zoom_chart, scroll_chart, reset_chart_view, "
                    "enter_replay, export_chart, create_annotation, clear_drawings, "
                    "clear_ai_annotations, toggle_indicator, remove_indicator",
    )
    params: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = Field(
        False,
        description="Whether user must approve this action before it runs.",
    )


class WalkthroughStep(BaseModel):
    """A single step in a guided analysis tour.

    Each step can have multiple simultaneous actions (e.g., draw fib +
    add RSI). Between steps, actions should reset unless ``keep_effects``
    is true.
    """
    explanation: str = Field(
        ...,
        description="User-facing explanation for this step — what we're doing and why.",
    )
    actions: List[GuidedAction] = Field(
        ...,
        description="Actions to execute simultaneously for this step.",
        min_length=1,
    )
    keep_effects: bool = Field(
        False,
        description="If true, previous step's chart effects (drawings, indicators) persist. "
                    "If false, clear non-essential drawings/indicators before applying this step.",
    )
    chart_freeze: bool = Field(
        True,
        description="Whether to freeze chart updates during this step.",
    )


class TourPlan(BaseModel):
    """Complete guided tour plan for Interact mode analysis.

    A walkthrough guides the user through visual steps on the chart with
    explanations. Each step can perform multiple actions simultaneously.
    """
    tour_id: str = Field(..., description="Unique tour identifier (auto-generated).")
    title: str = Field(..., description="Short title for the walkthrough.")
    steps: List[WalkthroughStep] = Field(
        ...,
        description="Ordered list of steps the user will progress through.",
        min_length=1,
    )
    summary: str = Field(
        ...,
        description="Recap / conclusion text shown after the walkthrough completes.",
    )
    chart_snapshot: Optional[Dict[str, Any]] = Field(
        None,
        description="Chart state (symbol, timeframe, indicators, drawings) to restore after tour.",
    )


# Legacy alias for backward-compatible imports
TourStepAction = GuidedAction
