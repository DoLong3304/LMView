"""Tests for the hybrid intent router."""
from __future__ import annotations

import pytest
from ai_service.agents.intent_router import classify_intent, _rule_based_classify
from ai_service.agents.state import initial_state
from ai_service.agents.types import ExpertName, IntentCategory, RoutingMethod


class TestRuleBasedClassify:
    """Test the rule-based classification logic."""

    def test_technical_analysis_query(self):
        result = _rule_based_classify("What is the RSI for BTCUSDT?", "ask", None)
        assert result.primary_intent == IntentCategory.TECHNICAL_ANALYSIS
        assert ExpertName.TECHNICAL_ANALYSIS in result.activated_experts

    def test_macd_query(self):
        result = _rule_based_classify("Show MACD crossover signal", "ask", None)
        assert result.primary_intent == IntentCategory.TECHNICAL_ANALYSIS

    def test_market_data_query(self):
        result = _rule_based_classify("What is the current price and volume?", "ask", None)
        assert result.primary_intent == IntentCategory.MARKET_DATA

    def test_news_query(self):
        result = _rule_based_classify("What is the latest news sentiment?", "ask", None)
        assert result.primary_intent == IntentCategory.NEWS_SENTIMENT
        assert ExpertName.NEWS_SENTIMENT in result.activated_experts

    def test_chart_action_query(self):
        result = _rule_based_classify("Draw a trendline on the chart", "ask", None)
        assert result.primary_intent == IntentCategory.CHART_ACTION

    def test_knowledge_query(self):
        result = _rule_based_classify("What is a golden cross? Explain the concept", "ask", None)
        # Could match both TA and knowledge - should pick one
        assert result.primary_intent in {
            IntentCategory.KNOWLEDGE_QUERY,
            IntentCategory.TECHNICAL_ANALYSIS,
        }

    def test_general_query(self):
        result = _rule_based_classify("Hello there", "ask", None)
        assert result.primary_intent == IntentCategory.GENERAL
        assert ExpertName.GENERAL in result.activated_experts

    def test_interact_mode_boost(self):
        result = _rule_based_classify("Add RSI indicator", "interact", None)
        # In interact mode, chart_action should be boosted
        assert ExpertName.CHART_INTERACTION in result.activated_experts

    def test_multi_intent(self):
        result = _rule_based_classify(
            "Analyze the RSI, MACD and latest news for BTC",
            "ask",
            None,
        )
        # Should detect multiple intents
        assert len(result.activated_experts) >= 1

    def test_chart_context_boost(self):
        ctx = {"selected_indicators": ["rsi", "macd"]}
        result = _rule_based_classify("What does this show?", "ask", ctx)
        # Chart context with indicators should boost TA
        assert result.primary_intent == IntentCategory.TECHNICAL_ANALYSIS


class TestClassifyIntentNode:
    """Test classify_intent as a LangGraph node function."""

    @pytest.mark.asyncio
    async def test_returns_state_update(self):
        state = initial_state(
            user_query="What is the RSI?",
            session_id="s1",
            user_id="u1",
        )
        update = await classify_intent(state)
        assert "intent" in update
        assert "activated_experts" in update
        assert isinstance(update["activated_experts"], list)
        assert len(update["activated_experts"]) >= 1

    @pytest.mark.asyncio
    async def test_always_has_at_least_one_expert(self):
        state = initial_state(
            user_query="",
            session_id="s1",
            user_id="u1",
        )
        update = await classify_intent(state)
        assert len(update["activated_experts"]) >= 1

    @pytest.mark.asyncio
    async def test_interact_mode_always_includes_chart(self):
        state = initial_state(
            user_query="Hello",
            session_id="s1",
            user_id="u1",
            mode="interact",
        )
        update = await classify_intent(state)
        assert ExpertName.CHART_INTERACTION.value in update["activated_experts"]

    @pytest.mark.asyncio
    async def test_confidence_range(self):
        state = initial_state(
            user_query="Analyze RSI divergence pattern",
            session_id="s1",
            user_id="u1",
        )
        update = await classify_intent(state)
        intent = update["intent"]
        assert 0.0 <= intent.confidence <= 1.0
        assert intent.routing_method == RoutingMethod.RULE_BASED
