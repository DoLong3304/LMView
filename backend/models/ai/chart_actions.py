"""
Pydantic models for chart actions — validation, recording, and execution state.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AIChartActionType(str, Enum):
    """Allowed chart actions the AI may propose."""
    PAUSE_LIVE_STREAM = "pause_live_stream"
    RESUME_LIVE_STREAM = "resume_live_stream"
    SET_VISIBLE_RANGE = "set_visible_range"
    ADD_INDICATOR = "add_indicator"
    REMOVE_INDICATOR = "remove_indicator"
    TOGGLE_INDICATOR = "toggle_indicator"
    TOGGLE_TIMEFRAME = "toggle_timeframe"
    TOGGLE_CHART = "toggle_chart"
    TOGGLE_MARKET = "toggle_market"
    DRAW_TRENDLINE = "draw_trendline"
    DRAW_TOOL = "draw_tool"
    HIGHLIGHT_REGION = "highlight_region"
    HIGHLIGHT_AREA = "highlight_area"
    HIGHLIGHT_CANDLE = "highlight_candle"
    HIGHLIGHT_INDICATOR = "highlight_indicator"
    MOVE_RESIZE_CHART = "move_resize_chart"
    REPLAY_CHART = "replay_chart"
    ADD_NOTE = "add_note"
    CAPTURE_CHART_SNAPSHOT = "capture_chart_snapshot"
    CLEAR_AI_ANNOTATIONS = "clear_ai_annotations"
    START_TOUR = "start_tour"
    VIEW_SECTION = "view_section"


class AIChartAction(BaseModel):
    """A single chart action proposed by the AI."""
    action_type: AIChartActionType
    params: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None
    requires_approval: bool = True


class AIChartActionValidateRequest(BaseModel):
    """Request to validate proposed chart actions."""
    actions: List[AIChartAction]


class AIChartActionRecordRequest(BaseModel):
    """Request to record action approval/execution state."""
    action_id: str
    approval_status: Optional[str] = None  # approved, rejected, edited
    execution_status: Optional[str] = None  # executed, failed
    error_message: Optional[str] = None


class AIChartActionValidationResult(BaseModel):
    """Result of chart action validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_actions: List[AIChartAction] = Field(default_factory=list)
