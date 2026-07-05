"""Knowledge Boundary — self-awareness for AI about its capabilities.

Prevents the AI from hallucinating answers outside its domain,
handles identity questions, and provides graceful refusal/redirection.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


# Patterns for identity/self-awareness questions
_SATOSHI_PATTERNS = [
    re.compile(r"\bwho\s+(?:is|was)\s+satoshi\s+nakamoto\b", re.IGNORECASE),
    re.compile(r"\bsatoshi\s+identity\b", re.IGNORECASE),
]

_SELF_AWARE_PATTERNS = [
    re.compile(r"\bwho (are|is) you\b", re.IGNORECASE),
    re.compile(r"\bwhat are you\b", re.IGNORECASE),
    re.compile(r"\byour name\b", re.IGNORECASE),
    re.compile(r"\bwhat can you do\b", re.IGNORECASE),
    re.compile(r"\bwhat is your purpose\b", re.IGNORECASE),
    re.compile(r"\btell me about yourself\b", re.IGNORECASE),
]

# LMView feature names that are not in current supported inventory.
# Guard these before LLM/RAG so benchmark/adversarial prompts cannot
# induce fake UI paths, readings, or action plans.
_UNSUPPORTED_LMVIEW_FEATURE_PATTERNS = [
    (re.compile(r"\bgann\s+square\s+of\s+nine\b", re.IGNORECASE), "Gann Square of Nine scanner"),
    (re.compile(r"\bfibonacci\s+time\s+zone\b", re.IGNORECASE), "Fibonacci Time Zone tool"),
    (re.compile(r"\bmarket\s+profile\b", re.IGNORECASE), "Market Profile indicator"),
    (re.compile(r"\bfootprint\b|\border\s+flow\s+imbalance\b", re.IGNORECASE), "Footprint / Order Flow Imbalance chart"),
    (re.compile(r"\belliott\s+wave\s+auto[-\s]?label", re.IGNORECASE), "Elliott Wave auto-labeler"),
    (re.compile(r"\bcumulative\s+delta\s+volume\b", re.IGNORECASE), "Cumulative Delta Volume indicator"),
    (re.compile(r"\bvolume\s+delta\s+heatmap\b", re.IGNORECASE), "Volume Delta heatmap chart type"),
    (re.compile(r"\bklinger\s+oscillator\b", re.IGNORECASE), "Klinger Oscillator"),
    (re.compile(r"\bstrategy\s+backtester\b|\bbacktester\b", re.IGNORECASE), "strategy backtester"),
    (re.compile(r"\bsmart\s+money\s+concepts\b|\bSMC\b", re.IGNORECASE), "Smart Money Concepts (SMC) indicator"),
    (re.compile(r"\bchaikin\s+money\s+flow\b|\bCMF\b", re.IGNORECASE), "Chaikin Money Flow (CMF) indicator"),
    (re.compile(r"\bDTOSC\b|\bdynamic\s+trading\s+oscillator\b", re.IGNORECASE), "DTOSC (Dynamic Trading Oscillator)"),
    (re.compile(r"\boptions\s+flow\s+dashboard\b", re.IGNORECASE), "options flow dashboard"),
    (re.compile(r"\bcoppock\s+curve\b", re.IGNORECASE), "Coppock Curve"),
]

_UNSUPPORTED_FEATURE_TEMPLATE = (
    "{feature} is not available or supported in LMView based on the current feature inventory. "
    "I do not have enough supported LMView context to provide readings, menu paths, or step-by-step usage for it. "
    "I can help with supported LMView tools such as candlestick charts, RSI, MACD, moving averages, "
    "Bollinger Bands, order book, recent trades, trendlines, Fibonacci retracement, and chart highlights."
)

_HARMFUL_PATTERNS = [
    re.compile(r"\bhack(?:ing)?\b|\bunauthorized\s+access\b|\bsteal\s+(?:an?\s+)?(?:account|password|key|token)\b", re.IGNORECASE),
]

_HARMFUL_TEMPLATE = (
    "I cannot help with hacking, unauthorized account access, credential theft, or other harmful activity. "
    "I can help with LMView account security basics and cryptocurrency market analysis."
)

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

    # Check known crypto identity uncertainty questions.
    for pattern in _SATOSHI_PATTERNS:
        if pattern.search(query_lower):
            return {
                "response": "Satoshi Nakamoto is the pseudonymous creator of Bitcoin, but their real-world identity remains unknown and unverified. I should not claim a specific person or group is Satoshi without reliable evidence.",
                "reason": "Satoshi identity uncertainty boundary.",
                "is_identity": False,
            }

    # Check self-awareness/identity questions
    for pattern in _SELF_AWARE_PATTERNS:
        if pattern.search(query_lower):
            return {
                "response": _IDENTITY_TEMPLATE,
                "reason": "Self-awareness query detected — providing identity response.",
                "is_identity": True,
            }

    # Check unsupported LMView feature requests before LLM/RAG.
    for pattern, feature in _UNSUPPORTED_LMVIEW_FEATURE_PATTERNS:
        if pattern.search(query):
            return {
                "response": _UNSUPPORTED_FEATURE_TEMPLATE.format(feature=feature),
                "reason": f"Unsupported LMView feature requested: {feature}.",
                "is_identity": False,
            }

    # Check harmful requests before LLM/RAG.
    for pattern in _HARMFUL_PATTERNS:
        if pattern.search(query):
            return {
                "response": _HARMFUL_TEMPLATE,
                "reason": "Harmful request refused.",
                "is_identity": False,
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
