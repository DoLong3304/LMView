"""
Mock provider — deterministic Phase 0 fallback.

Always available. Returns deterministic responses clearly marked as mock.
Preserves Phase 0 behavior when no real LLM is configured.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from backend.models.ai.providers import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    ProviderHealthStatus,
    ProviderInfo,
    ProviderType,
)
from backend.services.ai.base_provider import BaseProvider

logger = logging.getLogger("backend.services.ai.mock_provider")


class MockProvider(BaseProvider):
    """Deterministic mock provider — always available, no real LLM."""

    def __init__(self):
        super().__init__(provider_name="mock", model_name="phase0_mock")

    async def generate_chat_completion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        """Generate a deterministic mock response."""
        # Extract the user's last message
        user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        content = (
            f"[Mock AI Response] I received your message: "
            f'"{_truncate(user_message, 100)}". '
            f"This is a deterministic mock response from Phase 0. "
            f"No real LLM is connected. When a real provider is configured, "
            f"this will be replaced with grounded market analysis using "
            f"live data, indicators, and RAG knowledge retrieval.\n\n"
            f"⚠️ This response is not financial advice and should not be used "
            f"for trading decisions."
        )

        return LLMCompletionResponse(
            content=content,
            provider="mock",
            model_name="phase0_mock",
            is_mock=True,
            finish_reason="stop",
            token_input=self.estimate_tokens(user_message),
            token_output=self.estimate_tokens(content),
            latency_ms=1,
            metadata={"phase": "0", "deterministic": True},
        )

    async def health_check(self) -> ProviderHealthStatus:
        """Mock is always healthy."""
        return ProviderHealthStatus(
            provider_name="mock",
            is_healthy=True,
            latency_ms=0,
            model_loaded=True,
            checked_at=datetime.now(timezone.utc),
        )

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_name="mock",
            provider_type=ProviderType.MOCK,
            model_name="phase0_mock",
            is_local=True,
            is_available=True,
            priority=999,  # lowest priority — fallback only
            max_context_tokens=None,
            supports_structured_output=False,
            supports_streaming=False,
        )


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
