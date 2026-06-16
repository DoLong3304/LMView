"""
Context service — assembles chart context and data caveats for AI analysis.

Reads from existing backend services (Redis, InfluxDB, etc.) to build a
complete context package including data freshness warnings and news context.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai_service.context.news_context import build_news_context, NewsContextResult

logger = logging.getLogger("ai_service.context.context_service")


def assemble_data_caveats(chart_context: Optional[Dict[str, Any]]) -> List[str]:
    """
    Inspect chart context and generate data caveat warnings.

    These caveats tell the LLM what data limitations exist so it can
    state them honestly in its response.
    """
    caveats: List[str] = []

    if not chart_context:
        caveats.append("No chart context provided — analysis is limited.")
        return caveats

    # Market overview placeholder
    market = chart_context.get("market_overview_summary")
    if market and isinstance(market, dict):
        if market.get("is_placeholder", True):
            caveats.append(
                "Market overview data is PLACEHOLDER — do not treat as real analytics."
            )

    # Trade data caveat
    trades = chart_context.get("trades_summary")
    if trades and isinstance(trades, dict):
        if not trades.get("is_true_trade_tape", False):
            caveats.append(
                "Trade data is ticker-derived, NOT a true exchange trade tape. "
                "Trade volume and direction signals are approximate."
            )

    # Order book freshness
    ob = chart_context.get("orderbook_summary")
    if ob and isinstance(ob, dict):
        source = ob.get("source", "unknown")
        freshness = ob.get("freshness")
        if source in ("rest_fallback", "synthetic", "unknown"):
            caveats.append(
                f"Order book data source is '{source}' — may be stale or synthetic."
            )
        if freshness and isinstance(freshness, dict):
            if freshness.get("staleness_level") in ("stale", "very_stale"):
                caveats.append("Order book data appears stale.")

    # News availability
    news = chart_context.get("news_summary")
    if news and isinstance(news, dict):
        if news.get("article_count", 0) == 0:
            caveats.append(
                "News/sentiment data is unavailable for this analysis."
            )
        elif news.get("freshness") and isinstance(news["freshness"], dict):
            if news["freshness"].get("staleness_level") in ("stale", "very_stale"):
                caveats.append("News data is stale — sentiment may not reflect current conditions.")

    # Indicator data
    indicator_values = chart_context.get("indicator_values", [])
    if not indicator_values:
        caveats.append("No indicator values provided in chart context.")

    # Exchange caveat
    exchange = chart_context.get("exchange", "binance")
    if exchange and exchange.lower() == "okx":
        caveats.append(
            "OKX data path is experimental. WebSocket data handling may have gaps."
        )

    return caveats


async def assemble_news_context(
    chart_context: Optional[Dict[str, Any]],
    user_query: Optional[str] = None,
) -> Optional[NewsContextResult]:
    """
    Assemble news context from persisted PostgreSQL news data.

    Args:
        chart_context: Current chart context dict with symbol/exchange info.
        user_query: The user's question for keyword relevance scoring.

    Returns:
        NewsContextResult or None if news data is unavailable.
    """
    symbol = None
    if chart_context:
        symbol = chart_context.get("symbol")

    try:
        return await build_news_context(
            symbol=symbol,
            query=user_query,
        )
    except Exception as exc:
        logger.warning("Failed to build news context: %s", exc)
        return None


def build_context_summary(chart_context: Optional[Dict[str, Any]]) -> str:
    """Build a concise context summary string."""
    if not chart_context:
        return "No chart context provided."

    parts = []
    parts.append(f"Symbol: {chart_context.get('symbol', '?')}")
    parts.append(f"Exchange: {chart_context.get('exchange', 'binance')}")
    parts.append(f"Timeframe: {chart_context.get('timeframe', '?')}")

    indicators = chart_context.get("selected_indicators", [])
    if indicators:
        parts.append(f"Indicators: {', '.join(indicators[:5])}")

    return " | ".join(parts)
