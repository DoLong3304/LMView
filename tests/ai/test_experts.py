"""Tests for expert nodes — I/O contracts and structured output."""
from __future__ import annotations

import asyncio
import pytest
from ai_service.agents.state import initial_state
from ai_service.agents.types import ExpertOutput


class TestTechnicalAnalysisExpert:
    @pytest.fixture
    def expert(self):
        from ai_service.agents.experts.technical_analysis import TechnicalAnalysisExpert
        return TechnicalAnalysisExpert()

    @pytest.mark.asyncio
    async def test_no_data_returns_low_confidence(self, expert):
        state = initial_state(user_query="RSI?", session_id="s", user_id="u")
        output = await expert.safe_execute(state)
        assert isinstance(output, ExpertOutput)
        assert output.confidence <= 0.3

    @pytest.mark.asyncio
    async def test_with_rsi_data(self, expert):
        state = initial_state(
            user_query="RSI?",
            session_id="s",
            user_id="u",
            chart_context={
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "indicator_values": {"rsi": 25.0},
                "latest_candle": {"close": 65000},
            },
        )
        output = await expert.safe_execute(state)
        assert output.confidence > 0.3
        assert "oversold" in output.content.lower()
        assert output.structured_data.get("signals")

    @pytest.mark.asyncio
    async def test_with_multiple_indicators(self, expert):
        state = initial_state(
            user_query="Analysis",
            session_id="s",
            user_id="u",
            chart_context={
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "indicator_values": {
                    "rsi": 75.0,
                    "macd": 100,
                    "macd_signal": 80,
                    "sma20": 3500,
                    "sma50": 3400,
                },
                "latest_candle": {"close": 3550, "open": 3500, "high": 3600, "low": 3450},
            },
        )
        output = await expert.safe_execute(state)
        assert output.structured_data["trend_summary"] in {"bullish", "bearish", "neutral"}
        assert len(output.structured_data["signals"]) >= 2


class TestMarketDataExpert:
    @pytest.fixture
    def expert(self):
        from ai_service.agents.experts.market_data import MarketDataExpert
        return MarketDataExpert()

    @pytest.mark.asyncio
    async def test_no_context(self, expert):
        state = initial_state(user_query="Price?", session_id="s", user_id="u")
        output = await expert.safe_execute(state)
        assert output.confidence <= 0.3

    @pytest.mark.asyncio
    async def test_with_full_context(self, expert):
        state = initial_state(
            user_query="Market data",
            session_id="s",
            user_id="u",
            chart_context={
                "symbol": "BTCUSDT",
                "exchange": "binance",
                "latest_candle": {"close": 65000, "open": 64000, "volume": 1000},
                "orderbook_summary": {"best_bid": 64999, "best_ask": 65001, "spread": 2},
                "trades_summary": {"is_true_trade_tape": False},
            },
        )
        output = await expert.safe_execute(state)
        assert output.structured_data["ticker"]["close"] == 65000
        assert "ticker-derived" in str(output.warnings)


class TestGeneralExpert:
    @pytest.fixture
    def expert(self):
        from ai_service.agents.experts.general import GeneralExpert
        return GeneralExpert()

    @pytest.mark.asyncio
    async def test_basic_output(self, expert):
        state = initial_state(user_query="Hello", session_id="s", user_id="u")
        output = await expert.safe_execute(state)
        assert isinstance(output, ExpertOutput)
        assert output.expert_name == "general"


class TestChartInteractionExpert:
    @pytest.fixture
    def expert(self):
        from ai_service.agents.experts.chart_interaction import ChartInteractionExpert
        return ChartInteractionExpert()

    @pytest.mark.asyncio
    async def test_ask_mode_returns_low_confidence(self, expert):
        state = initial_state(user_query="Add RSI", session_id="s", user_id="u", mode="ask")
        output = await expert.safe_execute(state)
        assert output.confidence <= 0.4

    @pytest.mark.asyncio
    async def test_interact_mode_add_indicator(self, expert):
        state = initial_state(user_query="Add RSI indicator", session_id="s", user_id="u", mode="interact")
        output = await expert.safe_execute(state)
        actions = output.structured_data.get("proposed_actions", [])
        assert len(actions) >= 1
        assert actions[0]["tool"] == "add_indicator"
        assert actions[0]["params"]["indicator_name"] == "rsi"

    @pytest.mark.asyncio
    async def test_interact_mode_timeframe_switch(self, expert):
        state = initial_state(user_query="Switch to 4h timeframe", session_id="s", user_id="u", mode="interact")
        output = await expert.safe_execute(state)
        actions = output.structured_data.get("proposed_actions", [])
        tf_actions = [a for a in actions if a["tool"] == "set_timeframe"]
        assert len(tf_actions) >= 1
        assert tf_actions[0]["params"]["timeframe"] == "4h"
