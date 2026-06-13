"""Tests for reflection/validation node."""
from __future__ import annotations

import pytest
from ai_service.agents.reflection import validate_response, route_after_reflection
from ai_service.agents.state import initial_state
from ai_service.agents.types import (
    IntentCategory,
    IntentClassification,
    ExpertName,
    ExpertOutput,
    ValidationVerdict,
)


class TestValidateResponse:
    @pytest.mark.asyncio
    async def test_good_response_approved(self):
        state = initial_state(user_query="RSI?", session_id="s", user_id="u")
        state["synthesized_response"] = (
            "The RSI for BTCUSDT is currently at 45, which is in the neutral range. "
            "This suggests neither overbought nor oversold conditions. "
            "However, this is educational content and not financial advice. "
            "Trading carries significant risk."
        )
        state["expert_outputs"] = {}
        update = await validate_response(state)
        assert update["validation_result"].verdict == ValidationVerdict.APPROVED

    @pytest.mark.asyncio
    async def test_short_response_needs_revision(self):
        state = initial_state(user_query="RSI?", session_id="s", user_id="u")
        state["synthesized_response"] = "RSI is 45."
        state["expert_outputs"] = {}
        state["revision_count"] = 0
        update = await validate_response(state)
        assert update["validation_result"].verdict == ValidationVerdict.NEEDS_REVISION

    @pytest.mark.asyncio
    async def test_max_revisions_force_approval(self):
        state = initial_state(user_query="RSI?", session_id="s", user_id="u")
        state["synthesized_response"] = "Short."
        state["expert_outputs"] = {}
        state["revision_count"] = 2  # Already at max
        update = await validate_response(state)
        assert update["validation_result"].verdict == ValidationVerdict.APPROVED


class TestRouteAfterReflection:
    def test_approved_routes_to_approved(self):
        from ai_service.agents.types import ValidationResult
        state = initial_state(user_query="RSI?", session_id="s", user_id="u")
        state["validation_result"] = ValidationResult(verdict=ValidationVerdict.APPROVED)
        result = route_after_reflection(state)
        assert result == "approved"

    def test_needs_revision_routes_to_revision(self):
        from ai_service.agents.types import ValidationResult
        state = initial_state(user_query="RSI?", session_id="s", user_id="u")
        state["validation_result"] = ValidationResult(verdict=ValidationVerdict.NEEDS_REVISION)
        state["revision_count"] = 1
        result = route_after_reflection(state)
        assert result == "needs_revision"
