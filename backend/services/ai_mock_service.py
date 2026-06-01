"""
AI mock service — deterministic Phase 0 responses.

Generates context-aware responses that prove wiring without pretending to be an LLM.
Will be replaced by a real LLM provider in Phase 1+.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def generate_mock_response(
    message: str,
    mode: str = "ask",
    chart_context: Optional[Dict[str, Any]] = None,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a deterministic Phase 0 mock response.

    The response echoes back context to prove the wiring works,
    without pretending to be a real AI analysis.

    Returns:
        Dict with content, provider, model_name, is_mock, warnings, etc.
    """
    symbol = "unknown"
    timeframe = "unknown"
    exchange = "binance"
    indicator_count = 0
    indicators_list: List[str] = []

    if chart_context:
        symbol = chart_context.get("symbol", symbol)
        timeframe = chart_context.get("timeframe", timeframe)
        exchange = chart_context.get("exchange", exchange)
        indicators_list = chart_context.get("selected_indicators", [])
        indicator_count = len(indicators_list)

    # Build context summary
    context_parts = []
    context_parts.append(f"symbol={symbol}")
    context_parts.append(f"timeframe={timeframe}")
    context_parts.append(f"exchange={exchange}")
    if indicator_count > 0:
        context_parts.append(f"indicators={indicator_count} ({', '.join(indicators_list[:3])})")
    if chart_context and chart_context.get("latest_candle"):
        context_parts.append("latest_candle=present")
    if chart_context and chart_context.get("orderbook_summary"):
        context_parts.append("orderbook=present")

    context_summary = "; ".join(context_parts)

    # Mode-specific response
    if mode == "interact":
        content = (
            f"[Phase 0 — Interact Mode] AI backend foundation is connected. "
            f"Received context: {context_summary}. "
            f"Your message: \"{_truncate(message, 80)}\". "
            f"In Phase 1+, this mode will propose chart actions (add indicators, "
            f"draw trendlines, highlight regions) based on your request. "
            f"No chart actions are generated in Phase 0."
        )
    else:
        content = (
            f"[Phase 0 — Ask Mode] AI backend foundation is connected. "
            f"Received context: {context_summary}. "
            f"Your question: \"{_truncate(message, 80)}\". "
            f"In Phase 1+, this will return grounded market analysis using "
            f"live candle data, indicators, order book, and news sentiment. "
            f"Full LLM analysis is not enabled yet."
        )

    warnings = ["This is a Phase 0 mock response — no real LLM is connected."]

    # Suggested follow-up prompts
    suggested_actions = [
        f"What is the current trend for {symbol}?",
        f"Explain the RSI and MACD signals for {symbol}.",
        f"Find support and resistance levels for {symbol} on {timeframe}.",
    ]

    return {
        "content": content,
        "provider": "phase0_mock",
        "model_name": None,
        "is_mock": True,
        "warnings": warnings,
        "suggested_actions": suggested_actions,
        "chart_actions": None,
        "grounded_context_used": chart_context is not None,
    }


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
