"""Reflection / Validation node — quality gate with optional revision loop.

Checks the synthesized response for quality, safety, and completeness.
Can request up to MAX_REVISION_COUNT revisions before forcing approval.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from ai_service.agents.state import AgentState
from ai_service.agents.types import (
    MAX_REVISION_COUNT,
    Timer,
    ValidationResult,
    ValidationVerdict,
)

logger = logging.getLogger("ai_service.agents.reflection")

# Minimum response length to be considered complete
_MIN_RESPONSE_LENGTH = 50

# Patterns that indicate incomplete or problematic responses
_INCOMPLETE_PATTERNS = [
    re.compile(r"I cannot|I'm unable|I don't have access", re.IGNORECASE),
    re.compile(r"as an AI|as a language model", re.IGNORECASE),
]

# Required disclaimer patterns (at least one should be present for TA queries)
_DISCLAIMER_PATTERNS = [
    re.compile(r"not financial advice|disclaimer|educational|risk", re.IGNORECASE),
]


async def validate_response(state: AgentState) -> AgentState:
    """Validate the synthesized response quality.

    Returns a partial state update with validation_result and potentially
    incremented revision_count.
    """
    timer = Timer().start()
    response = state.get("synthesized_response", "")
    revision_count = state.get("revision_count", 0)
    intent = state.get("intent")
    expert_outputs = state.get("expert_outputs", {})

    issues: List[str] = []
    suggestions: List[str] = []

    # Check 1: Response length
    if len(response.strip()) < _MIN_RESPONSE_LENGTH:
        issues.append("Response is too short — may not adequately address the query.")
        suggestions.append("Expand the response with more detailed analysis.")

    # Check 2: Incomplete response patterns
    for pattern in _INCOMPLETE_PATTERNS:
        if pattern.search(response):
            issues.append("Response contains uncertainty language suggesting incomplete analysis.")
            suggestions.append("Use available expert data to provide concrete analysis.")
            break

    # Check 3: Disclaimer for TA/market queries
    if intent and intent.primary_intent.value in {"technical_analysis", "market_data"}:
        has_disclaimer = any(p.search(response) for p in _DISCLAIMER_PATTERNS)
        if not has_disclaimer and len(response) > 200:
            issues.append("Missing educational disclaimer for financial analysis.")
            suggestions.append("Add a brief disclaimer about educational purposes.")

    # Check 4: Expert data utilization
    available_experts = [name for name, out in expert_outputs.items() if out.content and not out.error]
    if available_experts and len(response) > 100:
        # Check if the response seems to ignore available data
        expert_keywords = {
            "technical_analysis": ["rsi", "macd", "sma", "indicator", "trend", "signal"],
            "market_data": ["price", "volume", "bid", "ask", "spread"],
            "news_sentiment": ["news", "sentiment", "headline", "article"],
            "rag_knowledge": ["knowledge", "document", "source"],
        }
        response_lower = response.lower()
        for expert_name in available_experts:
            keywords = expert_keywords.get(expert_name, [])
            if keywords and not any(kw in response_lower for kw in keywords):
                suggestions.append(f"Consider incorporating {expert_name} data in the response.")

    # Determine verdict
    score = 1.0 - (len(issues) * 0.2 + len(suggestions) * 0.05)
    score = max(0.1, min(1.0, score))

    if issues and revision_count < MAX_REVISION_COUNT:
        verdict = ValidationVerdict.NEEDS_REVISION
    elif issues and revision_count >= MAX_REVISION_COUNT:
        verdict = ValidationVerdict.APPROVED  # Force approval after max revisions
        logger.info("Max revisions (%d) reached; forcing approval.", MAX_REVISION_COUNT)
    else:
        verdict = ValidationVerdict.APPROVED

    validation = ValidationResult(
        verdict=verdict,
        score=score,
        issues=issues,
        suggestions=suggestions,
        reasoning=f"Score={score:.2f}, issues={len(issues)}, revisions={revision_count}/{MAX_REVISION_COUNT}",
    )

    timing = dict(state.get("timing", {}))
    timing["reflection"] = timer.elapsed_ms()

    new_revision_count = revision_count
    if verdict == ValidationVerdict.NEEDS_REVISION:
        new_revision_count += 1

    return {
        "validation_result": validation,
        "revision_count": new_revision_count,
        "timing": timing,
    }


def route_after_reflection(state: AgentState) -> str:
    """Conditional edge: route to output_guard (approved) or synthesis (revision).

    Used by LangGraph conditional_edges to determine the next node.
    """
    validation = state.get("validation_result")
    if validation and validation.verdict == ValidationVerdict.NEEDS_REVISION:
        logger.info("Reflection requested revision (count=%d).", state.get("revision_count", 0))
        return "needs_revision"
    return "approved"
