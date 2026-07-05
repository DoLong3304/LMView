"""General / Fallback Expert — handles queries that don't match specific experts.

Provides a baseline context summary for the synthesis node when no
specialized expert matches the query.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ai_service.agents.base_expert import BaseExpert
from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput

logger = logging.getLogger("ai_service.agents.experts.general")


class GeneralExpert(BaseExpert):
    """Fallback expert for general or ambiguous queries."""

    name = "general"

    async def execute(self, state: AgentState) -> ExpertOutput:
        """Build general context summary for the synthesis node."""
        chart_context = state.get("chart_context")
        symbol = state.get("symbol")
        timeframe = state.get("timeframe")
        exchange = state.get("exchange", "binance")
        user_query = state.get("user_query", "")

        structured: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "exchange": exchange,
            "query_length": len(user_query),
            "has_chart_context": chart_context is not None,
        }
        data_sources: List[str] = []

        parts: List[str] = []
        if symbol:
            parts.append(f"Symbol: {symbol}")
        if timeframe:
            parts.append(f"Timeframe: {timeframe}")
        if exchange:
            parts.append(f"Exchange: {exchange}")

        if chart_context:
            data_sources.append("chart_context")
            indicators = chart_context.get("selected_indicators", [])
            if indicators:
                parts.append(f"Active indicators: {', '.join(indicators[:5])}")
                structured["active_indicators"] = indicators

        content = "General context: " + " | ".join(parts) if parts else "No specific context available."

        return ExpertOutput(
            expert_name=self.name,
            content=content,
            structured_data=structured,
            # General expert is a fallback — low base confidence.
            # Slightly higher if we have actual context data.
            confidence=0.25 if not parts else 0.35,
            data_sources=data_sources,
        )
