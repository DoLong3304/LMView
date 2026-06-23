"""Expert Quality Ensemble — cross-validation and confidence voting.

After parallel expert execution, this ensemble compares expert outputs
for consistency, computes an aggregate confidence score, and detects
conflicting signals between experts.

Used by the synthesis node to weigh expert contributions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from ai_service.agents.types import ExpertOutput

logger = logging.getLogger("ai_service.agents.ensemble")

# Expert weight map — domain authority weights
_EXPERT_WEIGHTS: Dict[str, float] = {
    "technical_analysis": 0.30,
    "market_data": 0.25,
    "chart_interaction": 0.20,
    "rag_knowledge": 0.15,
    "news_sentiment": 0.10,
    "general": 0.0,  # Fallback, no weight
}

# Signal conflict detection pairs
_CONFLICT_PAIRS: List[Tuple[str, str]] = [
    ("technical_analysis.trend_summary", "market_data.summary"),
]


async def ensemble_vote(
    expert_outputs: Dict[str, ExpertOutput],
) -> Dict[str, Any]:
    """Run ensemble voting over all expert outputs.

    Steps:
    1. Collect structured signals from each expert
    2. Detect conflicts between related experts
    3. Compute weighted aggregate confidence
    4. Identify cross-validated signals vs single-source signals

    Returns:
        Dict with: aggregate_confidence, cross_validated_signals,
                   conflicting_signals, expert_summaries.
    """
    if not expert_outputs:
        return {
            "aggregate_confidence": 0.0,
            "cross_validated_signals": [],
            "conflicting_signals": [],
            "expert_summaries": [],
            "dominant_expert": "general",
        }

    # Collect signals and structured data
    signals: List[Dict[str, Any]] = []
    expert_summaries: List[Dict[str, Any]] = []
    weighted_confidences: List[float] = []
    total_weight = 0.0

    for name, output in expert_outputs.items():
        if output.error:
            continue

        weight = _EXPERT_WEIGHTS.get(name, 0.05)
        total_weight += weight

        weighted_confidences.append(weight * output.confidence)

        entry: Dict[str, Any] = {
            "expert": name,
            "confidence": output.confidence,
            "weight": weight,
            "summary": output.content[:200] if output.content else "",
        }

        # Extract structured signals
        structured = output.structured_data or {}
        signals.extend(structured.get("signals", []))
        entry["signals"] = structured.get("signals", [])

        expert_summaries.append(entry)

    # Aggregate confidence (weighted average)
    aggregate_confidence = sum(weighted_confidences) / total_weight if total_weight > 0 else 0.3

    # Detect conflicting signals
    conflicting_signals = _detect_conflicts(expert_outputs)

    # Detect cross-validated signals (signals that appear in multiple experts)
    cross_validated = _cross_validate_signals(expert_outputs)

    # Determine dominant expert
    dominant = max(
        expert_summaries,
        key=lambda e: e["confidence"] * e["weight"],
    ) if expert_summaries else {"expert": "general"}

    return {
        "aggregate_confidence": round(aggregate_confidence, 4),
        "cross_validated_signals": cross_validated,
        "conflicting_signals": conflicting_signals,
        "expert_summaries": expert_summaries,
        "dominant_expert": dominant.get("expert", "general"),
    }


def _detect_conflicts(
    expert_outputs: Dict[str, ExpertOutput],
) -> List[Dict[str, Any]]:
    """Detect conflicting signals between related experts."""
    conflicts: List[Dict[str, Any]] = []

    ta = expert_outputs.get("technical_analysis")
    md = expert_outputs.get("market_data")

    if ta and md and not ta.error and not md.error:
        ta_trend = (ta.structured_data or {}).get("trend_summary", "").lower()
        md_trend = (md.structured_data or {}).get("trend_summary", "").lower()

        if ta_trend and md_trend and ta_trend != md_trend:
            conflicts.append({
                "between": ["technical_analysis", "market_data"],
                "field": "trend_summary",
                "value_a": ta_trend,
                "value_b": md_trend,
                "severity": "medium",
            })

    return conflicts


def _cross_validate_signals(
    expert_outputs: Dict[str, ExpertOutput],
) -> List[Dict[str, Any]]:
    """Find signals that appear in multiple expert outputs.

    Cross-validated signals are more reliable than signals from a single source.
    """
    cross_validated: List[Dict[str, Any]] = []

    # Collect signals from each expert
    expert_signals: Dict[str, List[Dict[str, Any]]] = {}
    for name, output in expert_outputs.items():
        if output.error:
            continue
        sigs = (output.structured_data or {}).get("signals", [])
        if sigs:
            expert_signals[name] = sigs

    # Compare signals across experts by indicator type
    for name_a, sigs_a in expert_signals.items():
        for name_b, sigs_b in expert_signals.items():
            if name_a >= name_b:
                continue  # Only process each pair once
            for sig_a in sigs_a:
                indicator_a = sig_a.get("indicator", "")
                for sig_b in sigs_b:
                    indicator_b = sig_b.get("indicator", "")
                    # Match on indicator type or bias
                    if indicator_a == indicator_b and sig_a.get("bias") == sig_b.get("bias"):
                        cross_validated.append({
                            "indicator": indicator_a,
                            "bias": sig_a.get("bias"),
                            "sources": [name_a, name_b],
                            "signal": sig_a.get("signal"),
                        })

    return cross_validated
