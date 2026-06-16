"""Tests for AgentState schema, types, and initial state construction."""
from __future__ import annotations

import pytest
from ai_service.agents.types import (
    ExpertName,
    ExpertOutput,
    IntentCategory,
    IntentClassification,
    RoutingMethod,
    Timer,
    ValidationResult,
    ValidationVerdict,
    INTENT_TO_EXPERTS,
    DATA_ONLY_EXPERTS,
    MAX_REVISION_COUNT,
)
from ai_service.agents.state import AgentState, initial_state


class TestExpertOutput:
    def test_default_values(self):
        out = ExpertOutput(expert_name="test")
        assert out.expert_name == "test"
        assert out.content == ""
        assert out.confidence == 0.5
        assert out.error is None
        assert out.latency_ms == 0

    def test_to_dict(self):
        out = ExpertOutput(
            expert_name="technical_analysis",
            content="RSI oversold",
            confidence=0.8,
            data_sources=["chart_context"],
        )
        d = out.to_dict()
        assert d["expert_name"] == "technical_analysis"
        assert d["confidence"] == 0.8
        assert "chart_context" in d["data_sources"]

    def test_content_truncation_in_dict(self):
        out = ExpertOutput(expert_name="test", content="x" * 3000)
        d = out.to_dict()
        assert len(d["content"]) == 2000


class TestIntentClassification:
    def test_default_values(self):
        ic = IntentClassification(primary_intent=IntentCategory.GENERAL)
        assert ic.confidence == 0.5
        assert ic.routing_method == RoutingMethod.RULE_BASED
        assert ic.activated_experts == []

    def test_to_dict(self):
        ic = IntentClassification(
            primary_intent=IntentCategory.TECHNICAL_ANALYSIS,
            secondary_intents=[IntentCategory.MARKET_DATA],
            activated_experts=[ExpertName.TECHNICAL_ANALYSIS, ExpertName.MARKET_DATA],
            confidence=0.85,
        )
        d = ic.to_dict()
        assert d["primary_intent"] == "technical_analysis"
        assert "market_data" in d["secondary_intents"]
        assert len(d["activated_experts"]) == 2


class TestValidationResult:
    def test_approved(self):
        vr = ValidationResult(verdict=ValidationVerdict.APPROVED, score=0.9)
        assert vr.verdict == ValidationVerdict.APPROVED
        d = vr.to_dict()
        assert d["verdict"] == "approved"

    def test_needs_revision(self):
        vr = ValidationResult(
            verdict=ValidationVerdict.NEEDS_REVISION,
            issues=["Too short"],
            suggestions=["Expand analysis"],
        )
        d = vr.to_dict()
        assert len(d["issues"]) == 1


class TestInitialState:
    def test_basic_state(self):
        state = initial_state(
            user_query="What is the RSI for BTCUSDT?",
            session_id="sess-123",
            user_id="user-456",
        )
        assert state["user_query"] == "What is the RSI for BTCUSDT?"
        assert state["session_id"] == "sess-123"
        assert state["mode"] == "ask"
        assert state["exchange"] == "binance"
        assert state["expert_outputs"] == {}
        assert state["revision_count"] == 0

    def test_state_with_chart_context(self):
        ctx = {"symbol": "ETHUSDT", "timeframe": "4h", "exchange": "okx"}
        state = initial_state(
            user_query="Analyze",
            session_id="s1",
            user_id="u1",
            chart_context=ctx,
        )
        assert state["symbol"] == "ETHUSDT"
        assert state["timeframe"] == "4h"
        assert state["exchange"] == "okx"

    def test_state_with_interact_mode(self):
        state = initial_state(
            user_query="Add RSI",
            session_id="s1",
            user_id="u1",
            mode="interact",
        )
        assert state["mode"] == "interact"


class TestConstants:
    def test_max_revision_count(self):
        assert MAX_REVISION_COUNT == 2

    def test_intent_to_experts_mapping(self):
        assert ExpertName.TECHNICAL_ANALYSIS in INTENT_TO_EXPERTS[IntentCategory.TECHNICAL_ANALYSIS]
        assert ExpertName.GENERAL in INTENT_TO_EXPERTS[IntentCategory.GENERAL]

    def test_data_only_experts(self):
        assert "market_data" in DATA_ONLY_EXPERTS
        assert "rag_knowledge" in DATA_ONLY_EXPERTS
        assert "technical_analysis" not in DATA_ONLY_EXPERTS


class TestTimer:
    def test_timer_basics(self):
        timer = Timer()
        timer.start()
        import time
        time.sleep(0.01)
        elapsed = timer.elapsed_ms()
        assert elapsed >= 5  # At least a few ms
