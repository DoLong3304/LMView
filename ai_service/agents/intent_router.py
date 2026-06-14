"""Hybrid intent router — rule-based with optional LLM fallback.

Classifies user queries into intent categories and determines which experts
to activate. Uses keyword/regex heuristics first (zero LLM cost); falls
back to the LLM for ambiguous queries with low rule-based confidence.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from ai_service.agents.state import AgentState
from ai_service.agents.types import (
    ExpertName,
    IntentCategory,
    IntentClassification,
    INTENT_TO_EXPERTS,
    RoutingMethod,
    Timer,
)

logger = logging.getLogger("ai_service.agents.intent_router")

# Confidence threshold below which we attempt LLM-based classification
LLM_FALLBACK_THRESHOLD = 0.45

# ── Keyword sets for rule-based classification ────────────────────────────────

_TA_KEYWORDS: Set[str] = {
    "rsi", "macd", "ema", "sma", "bollinger", "vwap", "atr", "ichimoku",
    "supertrend", "fibonacci", "fib", "stochastic", "mfi", "psar",
    "support", "resistance", "trendline", "breakout", "breakdown",
    "overbought", "oversold", "divergence", "convergence", "golden cross",
    "death cross", "doji", "hammer", "engulfing", "indicator", "oscillator",
    "moving average", "momentum", "volatility", "trend", "reversal",
    "continuation", "pattern", "head", "shoulder", "double top",
    "double bottom", "triangle", "wedge", "channel", "technical",
    "analysis", "signal", "crossover", "zone",
}

_MARKET_KEYWORDS: Set[str] = {
    "price", "volume", "market", "order book", "orderbook", "depth",
    "bid", "ask", "spread", "liquidity", "whale", "flow", "ticker",
    "candle", "ohlc", "ohlcv", "trade", "trades", "buy", "sell",
    "long", "short", "leverage", "margin", "futures", "spot",
    "funding", "open interest", "dominance", "cap", "marketcap",
    "heatmap", "overview", "gainers", "losers", "screener",
}

_NEWS_KEYWORDS: Set[str] = {
    "news", "sentiment", "headline", "article", "report", "regulation",
    "sec", "cftc", "etf", "hack", "exploit", "partnership", "launch",
    "announcement", "forecast", "prediction", "outlook", "analyst",
    "bearish", "bullish", "fear", "greed", "event", "breaking",
}

_CHART_KEYWORDS: Set[str] = {
    "chart", "draw", "trendline", "highlight", "annotate", "annotation",
    "zoom", "scroll", "visible range", "timeframe", "switch", "fullscreen",
    "replay", "snapshot", "export", "add indicator", "remove indicator",
    "show me", "point out", "mark", "set range", "change chart",
}

_KNOWLEDGE_KEYWORDS: Set[str] = {
    "what is", "explain", "how does", "define", "definition", "mean",
    "concept", "learn", "tutorial", "guide", "documentation", "help",
    "lmview", "platform", "feature", "how to", "usage",
    "education", "risk", "portfolio", "diversification", "strategy",
}


def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent and determine which experts to activate.

    This is a LangGraph node function — it receives the full state and
    returns a partial state update with intent and activated_experts.
    """
    query = state.get("user_query", "")
    mode = state.get("mode", "ask")
    chart_context = state.get("chart_context")

    classification = _rule_based_classify(query, mode, chart_context)

    # Hybrid: if rule-based confidence is low, try LLM fallback
    if classification.confidence < LLM_FALLBACK_THRESHOLD:
        llm_classification = _llm_classify_intent(query, mode, chart_context)
        if llm_classification and llm_classification.confidence > classification.confidence:
            classification = llm_classification

    # Ensure we always activate at least one expert
    if not classification.activated_experts:
        classification.activated_experts = [ExpertName.GENERAL]

    # In interact mode, always include chart_interaction expert
    if mode == "interact" and ExpertName.CHART_INTERACTION not in classification.activated_experts:
        classification.activated_experts.append(ExpertName.CHART_INTERACTION)

    timer_ms = state.get("timing", {}).copy()
    timer_ms["intent_router"] = 0  # Updated by graph wrapper

    return {
        "intent": classification,
        "activated_experts": [e.value for e in classification.activated_experts],
        "timing": timer_ms,
    }


def _rule_based_classify(
    query: str,
    mode: str,
    chart_context: Optional[Dict[str, Any]],
) -> IntentClassification:
    """Rule-based intent classification using keyword scoring."""
    query_lower = query.lower().strip()
    words = set(re.findall(r"\b\w+\b", query_lower))
    # Also check 2-gram phrases
    bigrams = set()
    word_list = re.findall(r"\b\w+\b", query_lower)
    for i in range(len(word_list) - 1):
        bigrams.add(f"{word_list[i]} {word_list[i + 1]}")

    all_tokens = words | bigrams

    scores: Dict[IntentCategory, float] = {
        IntentCategory.TECHNICAL_ANALYSIS: len(all_tokens & _TA_KEYWORDS) * 1.2,
        IntentCategory.MARKET_DATA: len(all_tokens & _MARKET_KEYWORDS) * 1.0,
        IntentCategory.NEWS_SENTIMENT: len(all_tokens & _NEWS_KEYWORDS) * 1.1,
        IntentCategory.KNOWLEDGE_QUERY: len(all_tokens & _KNOWLEDGE_KEYWORDS) * 0.9,
        IntentCategory.CHART_ACTION: len(all_tokens & _CHART_KEYWORDS) * 1.3,
        IntentCategory.GENERAL: 0.1,  # Tiny baseline
    }

    # Boost chart_action if in interact mode
    if mode == "interact":
        scores[IntentCategory.CHART_ACTION] += 2.0

    # Boost TA if chart context has indicators
    if chart_context and chart_context.get("selected_indicators"):
        scores[IntentCategory.TECHNICAL_ANALYSIS] += 1.5

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0]
    primary_intent = primary[0]
    primary_score = primary[1]

    # Determine confidence from score magnitude
    total_score = sum(s for _, s in ranked)
    confidence = min(0.95, primary_score / max(total_score, 0.1) * 0.8 + 0.2) if primary_score > 0.5 else 0.3

    # Collect secondary intents with significant scores
    secondary_intents: List[IntentCategory] = []
    for intent, score in ranked[1:]:
        if score >= primary_score * 0.4 and score > 0.5:
            secondary_intents.append(intent)

    # Build activated expert list
    activated = list(INTENT_TO_EXPERTS.get(primary_intent, [ExpertName.GENERAL]))
    for sec in secondary_intents:
        for expert in INTENT_TO_EXPERTS.get(sec, []):
            if expert not in activated:
                activated.append(expert)

    # Always include RAG if it might help (knowledge or general queries)
    if ExpertName.RAG_KNOWLEDGE not in activated and primary_intent in {
        IntentCategory.KNOWLEDGE_QUERY,
        IntentCategory.GENERAL,
        IntentCategory.TECHNICAL_ANALYSIS,
    }:
        activated.append(ExpertName.RAG_KNOWLEDGE)

    return IntentClassification(
        primary_intent=primary_intent,
        secondary_intents=secondary_intents,
        activated_experts=activated,
        confidence=round(confidence, 3),
        routing_method=RoutingMethod.RULE_BASED,
        requires_chart_context=primary_intent in {
            IntentCategory.TECHNICAL_ANALYSIS,
            IntentCategory.CHART_ACTION,
            IntentCategory.MARKET_DATA,
        },
        requires_market_data=primary_intent in {
            IntentCategory.MARKET_DATA,
            IntentCategory.TECHNICAL_ANALYSIS,
        },
        reasoning=f"Rule-based: top={primary_intent.value}({primary_score:.1f}), "
                  f"secondary={[i.value for i in secondary_intents]}",
    )


def _llm_classify_intent(
    query: str,
    mode: str,
    chart_context: Optional[Dict[str, Any]],
) -> Optional[IntentClassification]:
    """LLM-based intent classification fallback.

    Currently returns None (no-op). When a local vLLM/LiteLLM provider
    is healthy, this will make a lightweight structured-output call to
    classify the query into intent categories.
    """
    # Phase 2: Implement LLM-based classification when provider is available.
    # The idea is to send a short system prompt asking the LLM to classify
    # the query into one of the IntentCategory values, returning JSON.
    # For now, fall through and let rule-based handle everything.
    logger.debug("LLM intent fallback not yet active for query: %s", query[:80])
    return None
