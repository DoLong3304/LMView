"""
Pydantic models for AI evaluation and golden question testing.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvalCategory(str, Enum):
    """Categories for golden evaluation questions."""
    TECHNICAL_INDICATOR = "technical_indicator"
    LIVE_CHART_ANALYSIS = "live_chart_analysis"
    LMVIEW_LIMITATION = "lmview_limitation"
    RAG_RETRIEVAL = "rag_retrieval"
    OUT_OF_SCOPE_REFUSAL = "out_of_scope_refusal"
    PROMPT_INJECTION_REFUSAL = "prompt_injection_refusal"
    STALE_DATA_WARNING = "stale_data_warning"
    BILINGUAL_RESPONSE = "bilingual_response"
    RISK_DISCLAIMER = "risk_disclaimer"
    MULTI_INTENT = "multi_intent"
    HALLUCINATION_BOUNDARY = "hallucination_boundary"
    CONSISTENCY = "consistency"
    WALKTHROUGH = "walkthrough"
    EDGE_CASE = "edge_case"
    CONFIGURATION = "configuration"
    CROSS_TURN_MEMORY = "cross_turn_memory"


class GoldenQuestion(BaseModel):
    """A single golden evaluation question with expected behavior."""
    id: str
    question: str
    language: str = "en"
    category: EvalCategory
    expected_behavior: str
    expected_scope: str = "in_scope"
    expected_contains: List[str] = Field(default_factory=list)
    expected_not_contains: List[str] = Field(default_factory=list)
    requires_rag: bool = False
    requires_chart_context: bool = False
    chart_context: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)


class EvalResult(BaseModel):
    """Result of evaluating a single golden question."""
    question_id: str
    passed: bool
    category: str
    actual_response: Optional[str] = None
    scope_correct: bool = True
    contains_check_passed: bool = True
    not_contains_check_passed: bool = True
    provider_used: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class EvalSuiteResult(BaseModel):
    """Aggregate results from running the full evaluation suite."""
    total_questions: int = 0
    passed: int = 0
    failed: int = 0
    error_count: int = 0
    pass_rate: float = 0.0
    category_results: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    results: List[EvalResult] = Field(default_factory=list)
    run_at: Optional[datetime] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    total_latency_ms: Optional[int] = None
