"""API-facing Pydantic models for multi-agent execution traces."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentExecutionSummary(BaseModel):
    """Summary of a single agent execution for API responses."""
    execution_id: str
    session_id: Optional[str] = None
    intent: Optional[str] = None
    activated_experts: List[str] = Field(default_factory=list)
    total_latency_ms: Optional[int] = None
    confidence: Optional[float] = None
    revision_count: int = 0
    orchestration_mode: str = "langgraph"
    provider: Optional[str] = None
    model_name: Optional[str] = None
    created_at: Optional[datetime] = None


class ExpertRunSummary(BaseModel):
    """Summary of a single expert run within an execution."""
    expert_name: str
    latency_ms: Optional[int] = None
    confidence: Optional[float] = None
    status: str = "success"
    data_sources: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class AgentExecutionDetail(BaseModel):
    """Full execution detail including expert runs."""
    execution: AgentExecutionSummary
    expert_runs: List[ExpertRunSummary] = Field(default_factory=list)
    token_usage: Dict[str, int] = Field(default_factory=dict)
    estimated_cost_usd: Optional[float] = None
    data_caveats: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
