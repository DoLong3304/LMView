"""
Pydantic models for AI chat sessions and messages.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.models.ai.tour import TourPlan

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


# ── Request DTOs ──────────────────────────────────────────────────────────────

class AIChatRequest(BaseModel):
    """Request body for POST /api/ai/chat."""
    session_id: Optional[str] = None
    mode: AIChatMode = AIChatMode.ASK
    message: str = Field(..., min_length=1, max_length=4000)
    language: Optional[str] = None
    chart_context: Optional[Dict[str, Any]] = None
    rag_enabled: Optional[bool] = Field(None, description="Override RAG on/off for ablation testing. None = use config default.")


class AISessionCreateRequest(BaseModel):
    """Request body for POST /api/ai/sessions."""
    title: Optional[str] = None
    mode: AIChatMode = AIChatMode.ASK
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    exchange: Optional[str] = "binance"


# ── Response DTOs ─────────────────────────────────────────────────────────────

class AIChatResponse(BaseModel):
    """Response from POST /api/ai/chat."""
    session_id: str
    message_id: str
    role: str = "assistant"
    content: str
    provider: str = "none"
    model_name: Optional[str] = None
    is_mock: bool = False
    created_at: Optional[datetime] = None
    warnings: List[str] = Field(default_factory=list)
    suggested_actions: Optional[List[str]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    chart_actions: Optional[List[Any]] = None
    grounded_context_used: bool = False
    # Phase 1 additions
    confidence: Optional[float] = None
    sources: Optional[List[Dict[str, Any]]] = None
    data_caveats: Optional[List[str]] = None
    provider_metadata: Optional[Dict[str, Any]] = None
    # Token usage for cost tracking
    token_input: Optional[int] = None
    token_output: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    # News context summary for frontend display
    news_context: Optional[Dict[str, Any]] = None
    # Tour plan for Interact mode guided analysis
    tour_plan: Optional[TourPlan] = None


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
    token_input: Optional[int] = None
    token_output: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Surfaced from metadata so a reloaded Interact-mode session can
    # show the Replay button without needing a new LLM call.
    tour_plan: Optional[TourPlan] = None
