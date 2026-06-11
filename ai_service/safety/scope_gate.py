"""
Scope gate service — keyword-based scope classification for Phase 0.

Determines whether a user message is in-scope for the LMView AI assistant.
Will be replaced by a more sophisticated classifier in Phase 1+.
"""
from __future__ import annotations

import re
from typing import Set

from backend.models.ai import ScopeCategory, ScopeGateResult

# In-scope keyword sets
_CRYPTO_KEYWORDS: Set[str] = {
    "bitcoin", "btc", "ethereum", "eth", "crypto", "altcoin", "token",
    "defi", "nft", "blockchain", "coin", "usdt", "usdc", "bnb", "sol",
    "ada", "xrp", "doge", "dot", "avax", "matic", "link", "uni",
    "market", "bull", "bear", "rally", "dump", "pump", "whale",
    "halving", "mining", "staking", "yield", "liquidity", "swap",
    "price", "trading", "trade", "buy", "sell", "long", "short",
    "leverage", "margin", "futures", "spot", "order",
}

_TECHNICAL_KEYWORDS: Set[str] = {
    "sma", "ema", "rsi", "macd", "bollinger", "vwap", "atr",
    "stochastic", "ichimoku", "supertrend", "fibonacci", "fib",
    "support", "resistance", "trendline", "breakout", "breakdown",
    "overbought", "oversold", "divergence", "convergence",
    "candle", "candlestick", "pattern", "head", "shoulder", "double",
    "indicator", "oscillator", "moving average", "volume",
    "momentum", "volatility", "trend", "reversal", "continuation",
    "golden cross", "death cross", "doji", "hammer", "engulfing",
}

_CHART_KEYWORDS: Set[str] = {
    "chart", "timeframe", "zoom", "draw", "annotation", "trendline",
    "replay", "fullscreen", "export", "snapshot", "highlight",
    "visible range", "candles", "bars", "line chart", "area chart",
}

_LMVIEW_KEYWORDS: Set[str] = {
    "lmview", "platform", "how to", "help", "tutorial", "feature",
    "watchlist", "settings", "theme", "dark mode", "light mode",
}

_NEWS_KEYWORDS: Set[str] = {
    "news", "sentiment", "headline", "article", "report", "analyst",
    "forecast", "prediction", "outlook", "regulation", "sec", "cftc",
}

_RISK_KEYWORDS: Set[str] = {
    "risk", "diversification", "portfolio", "allocation",
    "stop loss", "take profit", "risk reward", "position size",
    "money management", "drawdown",
}

# Out-of-scope patterns
_OUT_OF_SCOPE_PATTERNS = [
    re.compile(r"\b(weather|recipe|joke|poem|story|song|movie|game)\b", re.IGNORECASE),
    re.compile(r"\b(write me a|generate code|create a website)\b", re.IGNORECASE),
    re.compile(r"\b(personal advice|medical|legal|tax)\b", re.IGNORECASE),
    re.compile(r"\b(who (are|is) you|what are you|your name)\b", re.IGNORECASE),
    re.compile(r"\b(ignore previous|disregard|forget your|system prompt)\b", re.IGNORECASE),
]


def check_scope(message: str) -> ScopeGateResult:
    """
    Classify a user message for scope using keyword matching.

    Phase 0: simple keyword-based classification.
    Phase 1+: may use a lightweight classifier or LLM-based routing.

    Returns:
        ScopeGateResult with in_scope, category, reason, and confidence.
    """
    message_lower = message.lower().strip()
    words = set(re.findall(r"\b\w+\b", message_lower))

    # Check out-of-scope patterns first
    for pattern in _OUT_OF_SCOPE_PATTERNS:
        if pattern.search(message_lower):
            return ScopeGateResult(
                in_scope=False,
                category=ScopeCategory.OUT_OF_SCOPE,
                reason="Message appears to be outside the scope of crypto market analysis.",
                confidence=0.8,
            )

    # Score each category
    scores = {
        ScopeCategory.CRYPTO_MARKET_ANALYSIS: len(words & _CRYPTO_KEYWORDS),
        ScopeCategory.TECHNICAL_INDICATOR: len(words & _TECHNICAL_KEYWORDS),
        ScopeCategory.CHART_INTERACTION: len(words & _CHART_KEYWORDS),
        ScopeCategory.LMVIEW_USAGE: len(words & _LMVIEW_KEYWORDS),
        ScopeCategory.NEWS_SENTIMENT: len(words & _NEWS_KEYWORDS),
        ScopeCategory.RISK_EDUCATION: len(words & _RISK_KEYWORDS),
    }

    best_category = max(scores, key=lambda k: scores[k])
    best_score = scores[best_category]

    if best_score == 0:
        # No keywords matched — allow through with low confidence
        # since users may ask valid questions without exact keywords
        return ScopeGateResult(
            in_scope=True,
            category=ScopeCategory.CRYPTO_MARKET_ANALYSIS,
            reason="No specific category keywords matched; defaulting to in-scope.",
            confidence=0.3,
        )

    confidence = min(1.0, 0.5 + best_score * 0.1)

    return ScopeGateResult(
        in_scope=True,
        category=best_category,
        reason=f"Matched {best_score} keyword(s) for {best_category.value}.",
        confidence=confidence,
    )
