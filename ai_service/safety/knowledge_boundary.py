"""Knowledge Boundary — self-awareness for AI about its capabilities.

Prevents the AI from hallucinating answers outside its domain,
handles identity questions, and provides graceful refusal/redirection.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


# Patterns for identity/self-awareness questions
_SELF_AWARE_PATTERNS = [
    re.compile(r"\bwho (are|is) you\b", re.IGNORECASE),
    re.compile(r"\bwhat are you\b", re.IGNORECASE),
    re.compile(r"\byour name\b", re.IGNORECASE),
    re.compile(r"\bwhat can you do\b", re.IGNORECASE),
    re.compile(r"\bwhat is your purpose\b", re.IGNORECASE),
    re.compile(r"\btell me about yourself\b", re.IGNORECASE),
]

# Patterns for topics clearly out of knowledge boundary
_OUTSIDE_KNOWLEDGE_PATTERNS = [
    re.compile(r"\b(weather|recipe|cooking|baking)\b", re.IGNORECASE),
    re.compile(r"\b(write (a|me) (poem|story|song|joke))\b", re.IGNORECASE),
    re.compile(r"\b(medical|legal|tax) advice\b", re.IGNORECASE),
    re.compile(r"\b(create|build|develop) (a|an) (website|app|game)\b", re.IGNORECASE),
    re.compile(r"\b(what (happens|will) (tomorrow|next week))\b", re.IGNORECASE),
    re.compile(r"\b(stock|equity|forex|commodity) (market|price|trading)\b", re.IGNORECASE),
    re.compile(r"\b(predict|prediction|forecast) (price|market|bitcoin|btc|eth)\b", re.IGNORECASE),
]

# Identity response template
_IDENTITY_TEMPLATE = (
    "I am LMView AI Assistant, a specialized market analysis tool focused on cryptocurrency "
    "technical analysis. I can help you analyze charts, interpret indicators, detect patterns, "
    "and understand market trends. What cryptocurrency or chart would you like me to analyze?"
)

# Out-of-knowledge-boundary templates
_OUTSIDE_TEMPLATES: Dict[str, str] = {
    "weather": "I specialize in cryptocurrency market analysis and cannot provide weather information.",
    "recipe": "I am a market analysis assistant and cannot help with recipes or cooking.",
    "poem": "I am designed for cryptocurrency technical analysis, not creative writing.",
    "medical": "I cannot provide medical advice. Please consult a qualified healthcare professional.",
    "legal": "I cannot provide legal advice. Please consult a qualified attorney.",
    "tax": "I cannot provide tax advice. Please consult a qualified tax professional.",
    "stock": "I specialize in cryptocurrency markets. For stock market data, please use a dedicated stock analysis platform.",
    "predict": "I do not make price predictions. I provide technical analysis of market data to help inform your own trading decisions.",
}


def check_knowledge_boundary(query: str) -> Optional[Dict[str, Any]]:
    """Check if a query falls outside the AI's knowledge boundary.

    Returns:
        Dict with 'response' (predefined response) and 'reason' if out of bounds,
        or None if the query is within the knowledge boundary.
    """
    query_lower = query.lower().strip()

    # Check self-awareness/identity questions
    for pattern in _SELF_AWARE_PATTERNS:
        if pattern.search(query_lower):
            return {
                "response": _IDENTITY_TEMPLATE,
                "reason": "Self-awareness query detected — providing identity response.",
                "is_identity": True,
            }

    # Check out-of-knowledge topics
    for pattern in _OUTSIDE_KNOWLEDGE_PATTERNS:
        match = pattern.search(query_lower)
        if match:
            matched_text = match.group(0).lower()
            for key, template in _OUTSIDE_TEMPLATES.items():
                if key in matched_text:
                    return {
                        "response": template,
                        "reason": f"Query outside knowledge boundary: '{matched_text}'.",
                        "is_identity": False,
                    }
            # Generic fallback
            return {
                "response": "I can only help with cryptocurrency market analysis, technical indicators, chart interaction, and LMView platform usage.",
                "reason": f"Query outside knowledge boundary: '{matched_text}'.",
                "is_identity": False,
            }

    return None
