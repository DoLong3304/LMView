"""
Tour Plan models for Interact mode guided analysis tours.

Each tour is a sequence of actions with accompanying explanations
that the user progresses through self-paced.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TourStepAction(BaseModel):
    """A single step in a guided analysis tour.

    Each step has a chart action to execute and an explanation to show.
    """
    action_type: str = Field(
        ...,
        description="Chart action type: highlight_section, add_indicator, draw_tool, set_timeframe, etc.",
    )
    params: Dict[str, Any] = Field(default_factory=dict)
    explanation: str = Field(..., description="User-facing explanation for this step.")
    target_selector: Optional[str] = Field(
        None,
        description="CSS selector to highlight for this step.",
    )
    requires_approval: bool = Field(
        False,
        description="Whether user must click Execute before action runs.",
    )


class TourPlan(BaseModel):
    """Complete guided tour plan for Interact mode analysis."""
    tour_id: str = Field(..., description="Unique tour identifier.")
    title: str = Field(..., description="Short title for the tour.")
    steps: List[TourStepAction] = Field(
        ...,
        description="Ordered list of steps the user will progress through.",
        min_length=1,
    )
    summary: str = Field(
        ...,
        description="Recap text shown after tour completes.",
    )
    chart_snapshot: Optional[Dict[str, Any]] = Field(
        None,
        description="Chart state (symbol, timeframe) to restore after tour.",
    )
