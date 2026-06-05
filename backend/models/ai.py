"""
Pydantic models for AI chat, sessions, messages, and chart actions.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class AIChatMode(str, Enum):
    """AI chat operation modes."""
    ASK = "ask"
    INTERACT = "interact"


class AIMessageRole(str, Enum):
    """Allowed message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


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


class ScopeCategory(str, Enum):
    """Scope gate categories."""
    CRYPTO_MARKET_ANALYSIS = "crypto_market_analysis"
    TECHNICAL_INDICATOR = "technical_indicator"
    CHART_INTERACTION = "chart_interaction"
    LMVIEW_USAGE = "lmview_usage"
    NEWS_SENTIMENT = "news_sentiment"
    RISK_EDUCATION = "risk_education"
    OUT_OF_SCOPE = "out_of_scope"


# ── Request DTOs ──────────────────────────────────────────────────────────────

class AIChatRequest(BaseModel):
    """Request body for POST /api/ai/chat."""
    session_id: Optional[str] = None
    mode: AIChatMode = AIChatMode.ASK
    message: str = Field(..., min_length=1, max_length=4000)
    language: Optional[str] = None
    chart_context: Optional[Dict[str, Any]] = None


class AISessionCreateRequest(BaseModel):
    """Request body for POST /api/ai/sessions."""
    title: Optional[str] = None
    mode: AIChatMode = AIChatMode.ASK
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    exchange: Optional[str] = "binance"


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


# ── Response DTOs ─────────────────────────────────────────────────────────────

class AIChatResponse(BaseModel):
    """Response from POST /api/ai/chat."""
    session_id: str
    message_id: str
    role: str = "assistant"
    content: str
    provider: str = "phase0_mock"
    model_name: Optional[str] = None
    is_mock: bool = True
    created_at: Optional[datetime] = None
    warnings: List[str] = Field(default_factory=list)
    suggested_actions: Optional[List[str]] = None
    chart_actions: Optional[List[AIChartAction]] = None
    grounded_context_used: bool = False


class AISessionResponse(BaseModel):
    """AI chat session representation."""
    id: str
    user_id: str
    title: Optional[str] = None
    mode: str = "ask"
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    exchange: Optional[str] = "binance"
    status: str = "active"
    message_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AIMessageResponse(BaseModel):
    """Single AI message representation."""
    id: str
    session_id: str
    role: str
    content: str
    provider: Optional[str] = None
    model_name: Optional[str] = None
    is_mock: bool = False
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIHealthResponse(BaseModel):
    """Response from GET /api/ai/health."""
    auth_required: bool = True
    database_ready: bool = False
    mock_mode_available: bool = True
    chart_action_schema_version: str = "1.0.0"
    supported_modes: List[str] = Field(default_factory=lambda: ["ask", "interact"])
    supported_action_types: List[str] = Field(default_factory=list)


class ScopeGateResult(BaseModel):
    """Result of scope gate classification."""
    in_scope: bool = True
    category: ScopeCategory = ScopeCategory.CRYPTO_MARKET_ANALYSIS
    reason: str = ""
    confidence: float = 1.0


class AIChartActionValidationResult(BaseModel):
    """Result of chart action validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_actions: List[AIChartAction] = Field(default_factory=list)
