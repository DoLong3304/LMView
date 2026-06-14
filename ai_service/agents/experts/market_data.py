"""Market Data / Order Flow Expert — structures market context.

Gathers ticker, order book, and trade data from chart context and formats
it into structured data for the synthesis LLM call.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai_service.agents.base_expert import BaseExpert
from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput

logger = logging.getLogger("ai_service.agents.experts.market_data")


class MarketDataExpert(BaseExpert):
    """Structures market data, order book, and trade context."""

    name = "market_data"

    async def execute(self, state: AgentState) -> ExpertOutput:
        """Gather and structure market data from chart context."""
        chart_context = state.get("chart_context")
        symbol = state.get("symbol", "unknown")
        exchange = state.get("exchange", "binance")

        structured: Dict[str, Any] = {
            "symbol": symbol,
            "exchange": exchange,
            "ticker": {},
            "orderbook": {},
            "trades": {},
            "market_overview": {},
        }
        data_sources: List[str] = []
        analysis_parts: List[str] = []
        warnings: List[str] = []

        if not chart_context:
            return ExpertOutput(
                expert_name=self.name,
                content=f"No market data context available for {symbol}.",
                structured_data=structured,
                confidence=0.2,
                data_sources=[],
                warnings=["No chart context provided."],
            )

        # Latest candle / ticker data
        candle = chart_context.get("latest_candle")
        if candle and isinstance(candle, dict):
            structured["ticker"] = {
                "close": candle.get("close"),
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "volume": candle.get("volume"),
            }
            data_sources.append("latest_candle")
            close = candle.get("close")
            open_price = candle.get("open")
            if close and open_price:
                try:
                    change_pct = ((float(close) - float(open_price)) / float(open_price)) * 100
                    structured["ticker"]["change_pct"] = round(change_pct, 2)
                    direction = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
                    analysis_parts.append(
                        f"{symbol} price: {close} ({direction} {abs(change_pct):.2f}%)"
                    )
                except (ValueError, ZeroDivisionError):
                    pass

        # Order book summary
        ob = chart_context.get("orderbook_summary")
        if ob and isinstance(ob, dict):
            structured["orderbook"] = {
                "best_bid": ob.get("best_bid"),
                "best_ask": ob.get("best_ask"),
                "spread": ob.get("spread"),
                "imbalance": ob.get("imbalance"),
                "source": ob.get("source", "unknown"),
            }
            data_sources.append("orderbook")
            imbalance = ob.get("imbalance")
            if imbalance is not None:
                try:
                    imb_val = float(imbalance)
                    if abs(imb_val) > 0.3:
                        side = "buy-heavy" if imb_val > 0 else "sell-heavy"
                        analysis_parts.append(f"Order book imbalance: {side} ({imb_val:.2f})")
                except (ValueError, TypeError):
                    pass
            source = ob.get("source", "unknown")
            if source in ("rest_fallback", "synthetic", "unknown"):
                warnings.append(f"Order book source is '{source}' — may be stale.")

        # Trade summary
        trades = chart_context.get("trades_summary")
        if trades and isinstance(trades, dict):
            structured["trades"] = {
                "data_type": trades.get("data_type", "ticker_derived"),
                "is_true_trade_tape": trades.get("is_true_trade_tape", False),
                "recent_count": trades.get("trade_count"),
            }
            data_sources.append("trades")
            if not trades.get("is_true_trade_tape", False):
                warnings.append("Trade data is ticker-derived, not a true exchange trade tape.")

        # Market overview
        market = chart_context.get("market_overview_summary")
        if market and isinstance(market, dict):
            structured["market_overview"] = {
                "is_placeholder": market.get("is_placeholder", True),
                "btc_dominance": market.get("btc_dominance"),
                "total_market_cap": market.get("total_market_cap"),
            }
            data_sources.append("market_overview")
            if market.get("is_placeholder", True):
                warnings.append("Market overview is PLACEHOLDER data.")

        content = f"Market data for {symbol} on {exchange}:\n" + "\n".join(analysis_parts) if analysis_parts else f"Market data gathered for {symbol}."
        confidence = min(0.85, 0.2 + len(data_sources) * 0.15)

        return ExpertOutput(
            expert_name=self.name,
            content=content,
            structured_data=structured,
            confidence=confidence,
            data_sources=data_sources,
            warnings=warnings,
        )
