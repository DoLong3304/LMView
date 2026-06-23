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
        symbol = state.get("symbol", "unknown")
        exchange = state.get("exchange", "binance")
        timeframe = state.get("timeframe", "unknown")
        indicator_data = state.get("indicator_data")

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

        # Extract indicator values from chart context
        indicators = {}
        if chart_context:
            indicators = _extract_indicators(chart_context)
            if indicators:
                data_sources.append("chart_context")
        if indicator_data:
            indicators.update(indicator_data)
            data_sources.append("redis_indicators")

        # Fallback: Load indicators from Redis if empty
        if not indicators and symbol and symbol != "unknown":
            try:
                from backend.services.indicator_service import get_indicator_snapshot
                interval = timeframe if timeframe and timeframe != "unknown" else "1m"
                snapshot = await get_indicator_snapshot(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                )
                if snapshot and snapshot.indicators:
                    indicators.update({k: v for k, v in snapshot.indicators.items() if v is not None})
                    data_sources.append("redis_indicators")
            except Exception as exc:
                logger.warning("Failed to load indicators from Redis: %s", exc)

        if not indicators:
            return ExpertOutput(
                expert_name=self.name,
                content=f"No indicator data available for {symbol} on {timeframe}.",
                structured_data=structured,
                confidence=0.2,
                data_sources=data_sources,
                warnings=["No indicator data available in chart context or Redis."],
            )

        # Interpret each indicator
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
        macd_histogram = indicators.get("macd_histogram")
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
        ema12 = indicators.get("ema12")
        ema26 = indicators.get("ema26")
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

        if latest_close is not None and sma20 is not None:
            if float(latest_close) > float(sma20):
                analysis_parts.append(f"Price ({latest_close}) above SMA20 — short-term bullish.")

        # Bollinger Bands
        bb_upper = indicators.get("bb_upper") or indicators.get("bollinger_upper")
        bb_lower = indicators.get("bb_lower") or indicators.get("bollinger_lower")
        bb_middle = indicators.get("bb_middle") or indicators.get("bollinger_middle")
        if bb_upper is not None and bb_lower is not None and latest_close is not None:
            close = float(latest_close)
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

        # ── Candle pattern detection ──
        candles_data = None
        if chart_context:
            candles_data = chart_context.get("recent_candles")
        if not candles_data and symbol != "unknown":
            try:
                from backend.services.candle_service import get_candles_for_ai
                raw_candles = await get_candles_for_ai(symbol, exchange=exchange or "binance", interval=timeframe, count=50)
                if raw_candles:
                    candles_data = raw_candles
            except Exception as exc:
                logger.warning("Failed to fetch candles for AI: %s", exc)

        if candles_data:
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

            # Support / resistance
            sr = calculate_support_resistance(candles_data)
            structured["support_resistance"] = sr
            sr_summary = summarize_levels(sr)
            analysis_parts.append(f"Support/Resistance: {sr_summary}")

        # VWAP
        vwap = indicators.get("vwap")
        if vwap is not None and latest_close is not None:
            try:
                vwap_val = float(vwap)
                close = float(latest_close)
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
        confidence = min(0.9, 0.3 + len(signals) * 0.1)

        content = f"Technical analysis for {symbol} ({timeframe}):\n" + "\n".join(analysis_parts)

        return ExpertOutput(
            expert_name=self.name,
            content=content,
            structured_data=structured,
            confidence=confidence,
            data_sources=data_sources,
            warnings=warnings,
        )


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
