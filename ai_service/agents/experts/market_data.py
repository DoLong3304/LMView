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

class MarketDataExpert(BaseExpert):
    """Structures market data, order book, and trade context."""

    name = "market_data"

    async def execute(self, state: AgentState) -> ExpertOutput:
        """Gather and structure market data from chart context and Redis/DB."""
        chart_context = state.get("chart_context")
        primary_symbol = state.get("symbol") or (chart_context or {}).get("symbol") or "unknown"
        exchange = state.get("exchange", "binance")
        context_needs = state.get("context_needs")

        # Resolve list of symbols to process
        symbols = []
        if context_needs and context_needs.symbols:
            symbols = [s.upper() for s in context_needs.symbols if s]
        if not symbols and primary_symbol and primary_symbol != "unknown":
            symbols = [primary_symbol.upper()]
        if not symbols:
            return ExpertOutput(
                expert_name=self.name,
                content="No chart context or symbol was available for market data.",
                structured_data={"symbol": primary_symbol, "exchange": exchange, "ticker": {}, "orderbook": {}, "trades": {}},
                confidence=0.2,
                data_sources=[],
                warnings=["No chart context or symbol available."],
            )

        # Deduplicate while preserving order
        seen = set()
        unique_symbols = []
        for s in symbols:
            if s not in seen:
                seen.add(s)
                unique_symbols.append(s)

        results = []
        primary_upper = primary_symbol.upper() if primary_symbol else "unknown"
        for sym in unique_symbols:
            is_primary = (sym == primary_upper)
            ctx = chart_context if is_primary else None

            res = await self._analyze_single_symbol(
                symbol=sym,
                exchange=exchange,
                chart_context=ctx,
                context_needs=context_needs,
                state=state
            )
            results.append((sym, res))

        # Combine results
        combined_content_parts = []
        combined_structured = {
            "symbols": {}
        }
        combined_warnings = []
        combined_sources = []
        confidences = []

        for sym, res_data in results:
            combined_content_parts.append(res_data["content"])
            combined_structured["symbols"][sym] = res_data["structured"]
            combined_warnings.extend(res_data["warnings"])
            combined_sources.extend(res_data["data_sources"])
            confidences.append(res_data["confidence"])

        # Deduplicate warnings and sources
        combined_warnings = sorted(list(set(combined_warnings)))
        combined_sources = sorted(list(set(combined_sources)))

        # Also store primary symbol's data at the top level for backward compatibility
        primary_data = next((r for s, r in results if s == primary_upper), results[0][1] if results else None)
        if primary_data:
            combined_structured.update({
                "symbol": primary_symbol,
                "exchange": exchange,
                "ticker": primary_data["structured"].get("ticker", {}),
                "orderbook": primary_data["structured"].get("orderbook", {}),
                "trades": primary_data["structured"].get("trades", {}),
                "market_overview": primary_data["structured"].get("market_overview", {}),
            })

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.3
        combined_content = "\n\n".join(combined_content_parts)

        return ExpertOutput(
            expert_name=self.name,
            content=combined_content,
            structured_data=combined_structured,
            confidence=avg_confidence,
            data_sources=combined_sources,
            warnings=combined_warnings,
        )

    async def _analyze_single_symbol(
        self,
        symbol: str,
        exchange: str,
        chart_context: Optional[Dict[str, Any]],
        context_needs: Optional[ContextNeeds],
        state: AgentState
    ) -> Dict[str, Any]:
        """Perform market data structured analysis on a single symbol."""
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

        # Latest candle / ticker data
        candle = None
        if chart_context:
            candle = chart_context.get("latest_candle")

        # Fetch candle if missing
        if not candle and symbol != "unknown":
            try:
                from backend.services.candle_service import get_candles_for_ai
                tf_needed = (context_needs.timeframes or [state.get("timeframe", "1h")])[0] if context_needs else "1h"
                raw_candles = await get_candles_for_ai(
                    symbol, exchange=exchange or "binance",
                    interval=tf_needed, count=2,
                )
                if raw_candles:
                    candle = raw_candles[-1]
                    data_sources.append("db_ticker_fetch")
            except Exception as exc:
                logger.warning("Failed to fetch ticker candle for %s: %s", symbol, exc)

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
                        f"{symbol} price: ${float(close):,.2f} ({direction} {abs(change_pct):.2f}%)"
                    )
                except (ValueError, ZeroDivisionError, TypeError):
                    pass

        # Order book summary
        ob = None
        if chart_context:
            ob = chart_context.get("orderbook_summary")

        # Fetch order book from API/Redis directly if missing
        if not ob and symbol != "unknown":
            try:
                from backend.api.orderbook import get_orderbook_summary
                ob_data = await get_orderbook_summary(symbol, exchange)
                if ob_data:
                    ob = ob_data
                    data_sources.append("db_orderbook_fetch")
            except Exception as exc:
                logger.warning("Failed to fetch orderbook for %s: %s", symbol, exc)

        if ob and isinstance(ob, dict):
            structured["orderbook"] = {
                "best_bid": ob.get("best_bid"),
                "best_ask": ob.get("best_ask"),
                "spread": ob.get("spread"),
                "imbalance": ob.get("imbalance"),
                "source": ob.get("metadata", {}).get("source") if isinstance(ob.get("metadata"), dict) else ob.get("source", "unknown"),
            }
            data_sources.append("orderbook")
            imbalance = ob.get("imbalance")
            if imbalance is not None:
                try:
                    imb_val = float(imbalance)
                    if abs(imb_val) > 0.3:
                        side = "buy-heavy" if imb_val > 0 else "sell-heavy"
                        analysis_parts.append(f"{symbol} order book imbalance: {side} ({imb_val:.2f})")
                except (ValueError, TypeError):
                    pass
            if isinstance(ob.get("metadata"), dict):
                source = ob["metadata"].get("source") or ob.get("source", "unknown")
                is_stale = bool((ob["metadata"].get("freshness") or {}).get("is_stale", False))
            else:
                source = ob.get("source", "unknown")
                is_stale = False
            if source in ("rest_fallback", "synthetic", "unknown") or is_stale:
                warnings.append(f"{symbol} order book source is '{source}' — may be stale.")

        # Trade summary
        trades = chart_context.get("trades_summary") if chart_context else None
        if trades and isinstance(trades, dict):
            structured["trades"] = {
                "data_type": trades.get("data_type", "ticker_derived"),
                "is_true_trade_tape": trades.get("is_true_trade_tape", False),
                "recent_count": trades.get("trade_count"),
            }
            data_sources.append("trades")
            if not trades.get("is_true_trade_tape", False):
                warnings.append("Trade data is ticker-derived, not a true exchange trade tape.")

        # Market overview (only run for primary/overall)
        market = chart_context.get("market_overview_summary") if chart_context else None
        if market and isinstance(market, dict):
            structured["market_overview"] = {
                "is_placeholder": market.get("is_placeholder", True),
                "btc_dominance": market.get("btc_dominance"),
                "total_market_cap": market.get("total_market_cap"),
            }
            data_sources.append("market_overview")
            if market.get("is_placeholder", True):
                warnings.append("Market overview is PLACEHOLDER data.")

        # Confidence calculation
        has_price = bool(structured.get("ticker", {}).get("close"))
        has_volume = bool(structured.get("ticker", {}).get("volume"))
        has_orderbook = bool(structured.get("orderbook", {}).get("best_bid"))
        price_confidence = 0.5 if has_price else 0.0
        volume_bonus = 0.2 if has_volume else 0.0
        orderbook_bonus = 0.15 if has_orderbook else 0.0
        sources_bonus = min(0.15, len(data_sources) * 0.05)
        confidence = max(0.1, min(0.88, price_confidence + volume_bonus + orderbook_bonus + sources_bonus))

        content = f"Market data for {symbol} on {exchange}:\n" + "\n".join(analysis_parts) if analysis_parts else f"Market data gathered for {symbol}."

        return {
            "content": content,
            "structured": structured,
            "confidence": confidence,
            "data_sources": data_sources,
            "warnings": warnings,
        }
