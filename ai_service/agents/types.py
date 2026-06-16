"""Shared types for LangGraph multi-agent DAG.

Defines enums, data classes, and typed interfaces used across all agent nodes
and expert implementations.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Intent Enums ──────────────────────────────────────────────────────────────

class ExpertName(str, Enum):
    """Registered expert names in the DAG."""
    TECHNICAL_ANALYSIS = "technical_analysis"
    MARKET_DATA = "market_data"
    NEWS_SENTIMENT = "news_sentiment"
    RAG_KNOWLEDGE = "rag_knowledge"
    CHART_INTERACTION = "chart_interaction"
    GENERAL = "general"


class IntentCategory(str, Enum):
    """High-level intent categories produced by the intent router."""
    TECHNICAL_ANALYSIS = "technical_analysis"
    MARKET_DATA = "market_data"
    NEWS_SENTIMENT = "news_sentiment"
    KNOWLEDGE_QUERY = "knowledge_query"
    CHART_ACTION = "chart_action"
    GENERAL = "general"
    MULTI = "multi"


class RoutingMethod(str, Enum):
    """How the intent was classified."""
    RULE_BASED = "rule_based"
    LLM_FALLBACK = "llm_fallback"
    DEFAULT = "default"


class ValidationVerdict(str, Enum):
    """Reflection node verdict."""
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    FAILED = "failed"


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class IntentClassification:
    """Result of the hybrid intent router."""
    primary_intent: IntentCategory
    secondary_intents: List[IntentCategory] = field(default_factory=list)
    activated_experts: List[ExpertName] = field(default_factory=list)
    confidence: float = 0.5
    routing_method: RoutingMethod = RoutingMethod.RULE_BASED
    requires_chart_context: bool = False
    requires_market_data: bool = False
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "primary_intent": self.primary_intent.value,
            "secondary_intents": [i.value for i in self.secondary_intents],
            "activated_experts": [e.value for e in self.activated_experts],
            "confidence": self.confidence,
            "routing_method": self.routing_method.value,
            "requires_chart_context": self.requires_chart_context,
            "requires_market_data": self.requires_market_data,
            "reasoning": self.reasoning,
        }


@dataclass
class ExpertOutput:
    """Structured output from any expert node."""
    expert_name: str
    content: str = ""
    structured_data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    data_sources: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    latency_ms: int = 0
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "expert_name": self.expert_name,
            "content": self.content[:2000],
            "structured_data": self.structured_data,
            "confidence": self.confidence,
            "data_sources": self.data_sources,
            "token_usage": self.token_usage,
            "latency_ms": self.latency_ms,
            "warnings": self.warnings,
            "error": self.error,
        }


@dataclass
class ValidationResult:
    """Result from the reflection/validation node."""
    verdict: ValidationVerdict = ValidationVerdict.APPROVED
    score: float = 0.8
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "reasoning": self.reasoning,
        }


# ── Intent-to-Expert Mapping ─────────────────────────────────────────────────

INTENT_TO_EXPERTS: Dict[IntentCategory, List[ExpertName]] = {
    IntentCategory.TECHNICAL_ANALYSIS: [ExpertName.TECHNICAL_ANALYSIS],
    IntentCategory.MARKET_DATA: [ExpertName.MARKET_DATA],
    IntentCategory.NEWS_SENTIMENT: [ExpertName.NEWS_SENTIMENT],
    IntentCategory.KNOWLEDGE_QUERY: [ExpertName.RAG_KNOWLEDGE],
    IntentCategory.CHART_ACTION: [ExpertName.CHART_INTERACTION],
    IntentCategory.GENERAL: [ExpertName.GENERAL],
    IntentCategory.MULTI: [],  # populated by secondary_intents
}

# Experts that do NOT call the LLM — they gather and structure data.
# The synthesis node makes the single LLM call with all expert data.
DATA_ONLY_EXPERTS: set[str] = {
    ExpertName.MARKET_DATA.value,
    ExpertName.RAG_KNOWLEDGE.value,
    ExpertName.NEWS_SENTIMENT.value,
}

# Maximum revision loops before forcing approval
MAX_REVISION_COUNT = 2


class Timer:
    """Simple monotonic timer for measuring expert/node latency."""

    def __init__(self) -> None:
        self._start: float = 0.0

    def start(self) -> "Timer":
        self._start = time.monotonic()
        return self

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)
