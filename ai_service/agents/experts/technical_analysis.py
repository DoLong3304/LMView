"""Technical Analysis Expert — interprets indicators and chart patterns.

This expert gathers indicator data from the chart context and Redis,
then structures a technical analysis summary. It does NOT call the LLM
directly — the synthesis node handles the single LLM call with all expert
data assembled for best performance.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai_service.agents.base_expert import BaseExpert
from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput
from ai_service.context.pattern_detector import detect_patterns, detect_trend
from ai_service.context.support_resistance import calculate_support_resistance, summarize_levels

logger = logging.getLogger("ai_service.agents.experts.technical_analysis")

# Standard indicator interpretation thresholds
_RSI_OVERSOLD = 30
_RSI_OVERBOUGHT = 70


class TechnicalAnalysisExpert(BaseExpert):
    """Interprets technical indicators and chart patterns."""

    name = "technical_analysis"

    async def execute(self, state: AgentState) -> ExpertOutput:
        """Gather and interpret technical indicator data."""
        chart_context = state.get("chart_context")
        primary_symbol = state.get("symbol") or (chart_context or {}).get("symbol") or "unknown"
        exchange = state.get("exchange", "binance")
        timeframe = state.get("timeframe", "unknown")
        indicator_data = state.get("indicator_data")
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
                content="No chart context or symbol was available for technical analysis.",
                structured_data={"symbol": primary_symbol, "indicators": {}, "signals": []},
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
            ind_data = indicator_data if is_primary else None

            res = await self._analyze_single_symbol(
                symbol=sym,
                exchange=exchange,
                timeframe=timeframe,
                chart_context=ctx,
                indicator_data=ind_data,
                context_needs=context_needs
            )
            results.append((sym, res))

        # Combine results
        combined_content_parts = []
        combined_structured = {
            "timeframe": timeframe,
            "symbols": {}
        }
        combined_warnings = []
        combined_sources = []
        confidences = []

        for sym, res in results:
            combined_content_parts.append(res.content)
            combined_structured["symbols"][sym] = res.structured_data
            combined_warnings.extend(res.warnings)
            combined_sources.extend(res.data_sources)
            confidences.append(res.confidence)

        # Deduplicate warnings and sources
        combined_warnings = sorted(list(set(combined_warnings)))
        combined_sources = sorted(list(set(combined_sources)))

        # Also store primary symbol's data at the top level for backward compatibility
        primary_result = next((r for s, r in results if s == primary_upper), results[0][1] if results else None)
        if primary_result:
            combined_structured.update({
                "symbol": primary_symbol,
                "indicators": primary_result.structured_data.get("indicators", {}),
                "signals": primary_result.structured_data.get("signals", []),
                "trend_summary": primary_result.structured_data.get("trend_summary", "neutral"),
                "support_resistance": primary_result.structured_data.get("support_resistance"),
                "patterns": primary_result.structured_data.get("patterns"),
                "trend_info": primary_result.structured_data.get("trend_info"),
            })

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.3

        # Build comparison summary if multiple symbols were processed
        if len(unique_symbols) > 1:
            comparison_content = f"### Comparative Technical Analysis Summary ({timeframe}):\n"
            for sym, res in results:
                trend = res.structured_data.get("trend_summary", "neutral")
                rsi_val = ""
                rsi = res.structured_data.get("indicators", {}).get("rsi")
                if rsi is not None:
                    rsi_val = f" (RSI: {float(rsi):.1f})"
                comparison_content += f"- **{sym}**: {trend.upper()}{rsi_val}\n"
            comparison_content += "\n"
            combined_content = comparison_content + "\n\n".join(combined_content_parts)
        else:
            combined_content = combined_content_parts[0] if combined_content_parts else ""

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
        timeframe: str,
        chart_context: Optional[Dict[str, Any]],
        indicator_data: Optional[Dict[str, Any]],
        context_needs: Optional[ContextNeeds],
    ) -> ExpertOutput:
        """Perform technical analysis on a single symbol."""
        analysis_parts: List[str] = []
        structured: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": {},
            "signals": [],
            "trend_summary": "neutral",
        }
        data_sources: List[str] = []
        warnings: List[str] = []

        # Target indicators parsing
        target_indicators = None
        if context_needs and context_needs.indicators:
            target_indicators = {
                ind.lower().replace(" ", "_")
                for ind in context_needs.indicators
            }

        # Extract indicator values from chart context
        indicators = {}
        if chart_context:
            raw_indicators = _extract_indicators(chart_context)
            if target_indicators:
                for key in target_indicators:
                    if key in raw_indicators:
                        indicators[key] = raw_indicators[key]
                for raw_key, raw_val in raw_indicators.items():
                    if raw_key in target_indicators:
                        indicators[raw_key] = raw_val
            else:
                indicators = raw_indicators
            if indicators:
                data_sources.append("chart_context")
        if indicator_data:
            if target_indicators:
                for key in target_indicators:
                    if key in indicator_data:
                        indicators[key] = indicator_data[key]
            else:
                indicators.update(indicator_data)
            data_sources.append("redis_indicators")

        # Fallback: Load indicators from Redis if empty
        if not indicators and symbol and symbol != "unknown":
            try:
                from backend.services.indicator_service import get_indicator_snapshot
                interval = timeframe if timeframe and timeframe != "unknown" else "1h"
                snapshot = await get_indicator_snapshot(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                )
                if snapshot and snapshot.indicators:
                    indicators.update({k: v for k, v in snapshot.indicators.items() if v is not None})
                    data_sources.append("redis_indicators")
            except Exception as exc:
                logger.warning("Failed to load indicators from Redis for %s: %s", symbol, exc)

        if not indicators:
            return ExpertOutput(
                expert_name=self.name,
                content=f"No indicator data available for {symbol} on {timeframe}.",
                structured_data=structured,
                confidence=0.2,
                data_sources=data_sources,
                warnings=[f"No indicator data available for {symbol} in chart context or Redis."],
            )

        structured["indicators"] = indicators
        signals: List[Dict[str, Any]] = []

        # RSI interpretation
        rsi = indicators.get("rsi") or indicators.get("rsi14")
        if rsi is not None:
            rsi_val = float(rsi)
            if rsi_val <= _RSI_OVERSOLD:
                signals.append({"indicator": "RSI", "signal": "oversold", "value": rsi_val, "bias": "bullish"})
                analysis_parts.append(f"RSI at {rsi_val:.1f} — oversold territory, potential reversal setup.")
            elif rsi_val >= _RSI_OVERBOUGHT:
                signals.append({"indicator": "RSI", "signal": "overbought", "value": rsi_val, "bias": "bearish"})
                analysis_parts.append(f"RSI at {rsi_val:.1f} — overbought territory, potential pullback.")
            else:
                signals.append({"indicator": "RSI", "signal": "neutral", "value": rsi_val, "bias": "neutral"})
                analysis_parts.append(f"RSI at {rsi_val:.1f} — neutral range.")

        # MACD interpretation
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        if macd is not None and macd_signal is not None:
            macd_val = float(macd)
            signal_val = float(macd_signal)
            if macd_val > signal_val:
                signals.append({"indicator": "MACD", "signal": "bullish_crossover", "bias": "bullish"})
                analysis_parts.append("MACD above signal line — bullish momentum.")
            else:
                signals.append({"indicator": "MACD", "signal": "bearish_crossover", "bias": "bearish"})
                analysis_parts.append("MACD below signal line — bearish momentum.")

        # SMA/EMA trend
        sma20 = indicators.get("sma20")
        sma50 = indicators.get("sma50")
        latest_close = _get_latest_close(chart_context)

        if sma20 is not None and sma50 is not None:
            sma20_val = float(sma20)
            sma50_val = float(sma50)
            if sma20_val > sma50_val:
                signals.append({"indicator": "SMA", "signal": "uptrend", "bias": "bullish"})
                analysis_parts.append(f"SMA20 ({sma20_val:.2f}) above SMA50 ({sma50_val:.2f}) — uptrend.")
            else:
                signals.append({"indicator": "SMA", "signal": "downtrend", "bias": "bearish"})
                analysis_parts.append(f"SMA20 ({sma20_val:.2f}) below SMA50 ({sma50_val:.2f}) — downtrend.")

        # Bollinger Bands
        bb_upper = indicators.get("bb_upper") or indicators.get("bollinger_upper")
        bb_lower = indicators.get("bb_lower") or indicators.get("bollinger_lower")
        bb_middle = indicators.get("bb_middle") or indicators.get("bollinger_middle")
        if bb_upper is not None and bb_lower is not None:
            # Estimate close from indicators if missing
            close = float(latest_close) if latest_close is not None else float(bb_middle) if bb_middle is not None else None
            if close is not None:
                upper = float(bb_upper)
                lower = float(bb_lower)
                bb_width = upper - lower
                if close >= upper:
                    signals.append({"indicator": "Bollinger", "signal": "upper_touch", "bias": "bearish"})
                    analysis_parts.append("Price at upper Bollinger Band — potential resistance.")
                elif close <= lower:
                    signals.append({"indicator": "Bollinger", "signal": "lower_touch", "bias": "bullish"})
                    analysis_parts.append("Price at lower Bollinger Band — potential support.")
                elif bb_middle is not None:
                    middle = float(bb_middle)
                    if close > middle:
                        analysis_parts.append("Price is trading in the upper half of the Bollinger Bands — bullish bias.")
                    else:
                        analysis_parts.append("Price is trading in the lower half of the Bollinger Bands — bearish bias.")
                if bb_width > 0:
                    structured["indicators"]["bb_width"] = round(bb_width, 4)

        # Volatility (ATR)
        atr = indicators.get("atr14") or indicators.get("atr")
        if atr is not None:
            atr_val = float(atr)
            structured["indicators"]["atr"] = atr_val
            analysis_parts.append(f"Average True Range (ATR): {atr_val:.4f} — indicating standard price volatility levels.")

        # Volume MA
        vol = indicators.get("volume") or indicators.get("candle_volume")
        vol_ma = indicators.get("volume_sma20") or indicators.get("volume_ma") or indicators.get("volumeMa")
        if vol is not None and vol_ma is not None:
            try:
                vol_val = float(vol)
                vol_ma_val = float(vol_ma)
                if vol_val > vol_ma_val * 1.5:
                    signals.append({"indicator": "Volume", "signal": "high_volume", "bias": "neutral"})
                    analysis_parts.append(f"Volume is significantly elevated ({vol_val:.1f} vs average {vol_ma_val:.1f}) — indicating strong trading participation.")
                else:
                    analysis_parts.append(f"Volume is within standard average range ({vol_val:.1f} vs average {vol_ma_val:.1f}).")
            except (ValueError, TypeError):
                pass

        # Candlestick pattern detection
        candles_data = None
        if chart_context:
            candles_data = chart_context.get("recent_candles")

        # Fetch candles if missing
        if not candles_data and symbol != "unknown":
            try:
                from backend.services.candle_service import get_candles_for_ai
                interval = timeframe if timeframe and timeframe != "unknown" else "1h"
                raw_candles = await get_candles_for_ai(symbol, exchange=exchange or "binance", interval=interval, count=50)
                if raw_candles:
                    candles_data = raw_candles
                    data_sources.append("db_candles")
            except Exception as exc:
                logger.warning("Failed to fetch candles for %s: %s", symbol, exc)

        if candles_data:
            # Detect patterns and S/R on RAW candles
            patterns = detect_patterns(candles_data)
            if patterns:
                structured["patterns"] = patterns
                for p in patterns:
                    signals.append({"indicator": f"pattern:{p['name']}", "signal": p.get("direction", "neutral"), "bias": p.get("direction")})
                    analysis_parts.append(f"Candlestick pattern detected: {p['description']}")
            trend_info = detect_trend(candles_data)
            structured["trend_info"] = trend_info
            if trend_info["direction"] != "neutral":
                analysis_parts.append(f"Short-term trend: {trend_info['direction']} (strength: {trend_info.get('strength', 0):.2f})")

            sr = calculate_support_resistance(candles_data)
            structured["support_resistance"] = sr
            sr_summary = summarize_levels(sr)
            analysis_parts.append(f"Support/Resistance: {sr_summary}")

            # Apply statistical compaction to save token space in synthesis context
            structured["candles_compacted"] = compact_candles(candles_data, max_candles=15)

        # VWAP
        vwap = indicators.get("vwap")
        if vwap is not None:
            close = float(latest_close) if latest_close is not None else float(bb_middle) if bb_middle is not None else None
            if close is not None:
                try:
                    vwap_val = float(vwap)
                    if close > vwap_val:
                        signals.append({"indicator": "VWAP", "signal": "above_vwap", "bias": "bullish"})
                        analysis_parts.append(f"Price is trading above VWAP ({vwap_val:.2f}) — intraday bullish bias.")
                    else:
                        signals.append({"indicator": "VWAP", "signal": "below_vwap", "bias": "bearish"})
                        analysis_parts.append(f"Price is trading below VWAP ({vwap_val:.2f}) — intraday bearish bias.")
                except (ValueError, TypeError):
                    pass

        # Determine overall trend
        bullish_count = sum(1 for s in signals if s.get("bias") == "bullish")
        bearish_count = sum(1 for s in signals if s.get("bias") == "bearish")
        if bullish_count > bearish_count:
            structured["trend_summary"] = "bullish"
        elif bearish_count > bullish_count:
            structured["trend_summary"] = "bearish"
        else:
            structured["trend_summary"] = "neutral"

        structured["signals"] = signals

        # Confidence calculation
        extremity_sum = 0.0
        extremity_count = 0
        for s in signals:
            val = s.get("value")
            if val is not None:
                try:
                    fval = float(val)
                    if s.get("indicator") in ("RSI",):
                        extremity_sum += min(1.0, abs(fval - 50) / 30.0)
                        extremity_count += 1
                    elif s.get("indicator") in ("MACD", "Bollinger"):
                        extremity_sum += 0.6
                        extremity_count += 1
                except (ValueError, TypeError):
                    pass
        avg_extremity = (extremity_sum / max(extremity_count, 1)) if extremity_count > 0 else 0.3

        if signals:
            bias_counts: Dict[str, int] = {}
            for s in signals:
                b = s.get("bias", "neutral")
                bias_counts[b] = bias_counts.get(b, 0) + 1
            dominant_count = max(bias_counts.values())
            convergence = dominant_count / len(signals)
        else:
            convergence = 0.0

        signal_freshness = min(1.0, len(indicators) / 5.0)

        confidence = max(0.15, min(0.92,
            avg_extremity * 0.35 +
            convergence * 0.35 +
            signal_freshness * 0.15 +
            min(1.0, len(signals) / 6.0) * 0.15
        ))

        content = f"Technical analysis for {symbol} ({timeframe}):\n" + "\n".join(analysis_parts)

        return ExpertOutput(
            expert_name=self.name,
            content=content,
            structured_data=structured,
            confidence=confidence,
            data_sources=data_sources,
            warnings=warnings,
        )

# Helper functions for compaction
import math

def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)

def _select_key_candles(candles: List[Dict[str, Any]], count: int = 15) -> List[Dict[str, Any]]:
    """Select a subset of candles representing endpoints, extremes, and pivots."""
    if len(candles) <= count:
        return candles

    selected_indices = {0, 1, 2, len(candles) - 1, len(candles) - 2, len(candles) - 3, len(candles) - 4, len(candles) - 5}

    for i in range(2, len(candles) - 2):
        is_high = candles[i]["high"] == max(candles[j]["high"] for j in range(i-2, i+3))
        is_low = candles[i]["low"] == min(candles[j]["low"] for j in range(i-2, i+3))
        if is_high or is_low:
            selected_indices.add(i)

    sorted_indices = sorted(list(selected_indices))
    if len(sorted_indices) > count:
        endpoints = sorted_indices[:3] + sorted_indices[-5:]
        middle = sorted_indices[3:-5]
        sampled_middle = [middle[i] for i in range(0, len(middle), max(1, len(middle) // (count - 8)))]
        sorted_indices = sorted(list(set(endpoints + sampled_middle)))[:count]
    elif len(sorted_indices) < count:
        step = max(1, len(candles) // (count - len(sorted_indices)))
        for i in range(0, len(candles), step):
            selected_indices.add(i)
        sorted_indices = sorted(list(selected_indices))[:count]

    return [candles[idx] for idx in sorted_indices]

def _quartile_summary(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    closes = sorted([c["close"] for c in candles])
    n = len(closes)
    return {
        "min": closes[0],
        "q1": closes[n // 4],
        "median": closes[n // 2],
        "q3": closes[(3 * n) // 4],
        "max": closes[-1],
    }

def compact_candles(candles: List[Dict[str, Any]], max_candles: int = 15) -> Dict[str, Any]:
    """Compact candle array into statistical summary + key candles."""
    if not candles:
        return {"candles": [], "compacted": False}
    if len(candles) <= max_candles:
        return {"candles": candles, "compacted": False}

    closes = [c["close"] for c in candles]
    return {
        "compacted": True,
        "total_candles": len(candles),
        "time_range": {"start": candles[0].get("time"), "end": candles[-1].get("time")},
        "ohlcv_summary": {
            "open_first": candles[0]["open"],
            "close_last": candles[-1]["close"],
            "high_max": max(c["high"] for c in candles),
            "low_min": min(c["low"] for c in candles),
            "volume_total": sum(c["volume"] for c in candles),
            "volume_avg": sum(c["volume"] for c in candles) / len(candles),
            "avg_close": sum(closes) / len(candles),
            "close_std": round(_std(closes), 4),
            "price_change_pct": round(((candles[-1]["close"] - candles[0]["open"]) / candles[0]["open"]) * 100, 2),
        },
        "key_candles": _select_key_candles(candles, count=max_candles),
        "quartile_summary": _quartile_summary(candles),
    }


def _extract_indicators(chart_context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract indicator values from chart context dict."""
    indicators = {}
    # Direct indicator values
    iv = chart_context.get("indicator_values")
    if iv and isinstance(iv, dict):
        indicators.update(iv)
    elif iv and isinstance(iv, list):
        # Batch 4 format: list of {name, value, signal, params}
        for item in iv:
            if isinstance(item, dict):
                name = item.get("name")
                val = item.get("value")
                if name and val is not None:
                    indicators[name] = val
                    sig = item.get("signal")
                    if sig:
                        indicators[f"{name}_signal"] = sig
    # Latest candle has some derived values
    candle = chart_context.get("latest_candle")
    if candle and isinstance(candle, dict):
        for key in ("volume", "close", "open", "high", "low"):
            if key in candle:
                indicators[f"candle_{key}"] = candle[key]
    return indicators


def _get_latest_close(chart_context: Optional[Dict[str, Any]]) -> Optional[float]:
    """Extract latest close price from chart context."""
    if not chart_context:
        return None
    candle = chart_context.get("latest_candle")
    if candle and isinstance(candle, dict):
        close = candle.get("close")
        if close is not None:
            try:
                return float(close)
            except (ValueError, TypeError):
                pass
    return None
