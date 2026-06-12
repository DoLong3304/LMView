"""
Common AI models — health, scope gate, shared enums.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ScopeCategory(str, Enum):
    """Scope gate categories."""
    CRYPTO_MARKET_ANALYSIS = "crypto_market_analysis"
    TECHNICAL_INDICATOR = "technical_indicator"
    CHART_INTERACTION = "chart_interaction"
    LMVIEW_USAGE = "lmview_usage"
    NEWS_SENTIMENT = "news_sentiment"
    RISK_EDUCATION = "risk_education"
    OUT_OF_SCOPE = "out_of_scope"


class ScopeGateResult(BaseModel):
    """Result of scope gate classification."""
    in_scope: bool = True
    category: ScopeCategory = ScopeCategory.CRYPTO_MARKET_ANALYSIS
    reason: str = ""
    confidence: float = 1.0


class AIHealthResponse(BaseModel):
    """Response from GET /api/ai/health."""
    auth_required: bool = True
    database_ready: bool = False
    mock_mode_available: bool = False
    chart_action_schema_version: str = "1.0.0"
    supported_modes: List[str] = Field(default_factory=lambda: ["ask", "interact"])
    supported_action_types: List[str] = Field(default_factory=list)
    # Phase 1 additions
    ai_mode: Optional[str] = None
    provider_mode: Optional[str] = None
    effective_provider: Optional[str] = None
    available_api_models: List[str] = Field(default_factory=list)
    local_available: bool = False
    action_catalog_version: Optional[str] = None
    rag_enabled: bool = False
    real_llm_enabled: bool = False
    available_providers: Optional[List[str]] = None
    pgvector_ready: bool = False
    knowledge_source_count: int = 0
