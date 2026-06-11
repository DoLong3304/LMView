"""Generic no-LLM provider.

Used when no local/API model is available. This is not mock data: it gives
bounded system help and avoids pretending to analyze markets without a model.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from backend.models.ai.providers import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    ProviderHealthStatus,
    ProviderInfo,
    ProviderType,
)
from ai_service.providers.base import BaseProvider


class NoneProvider(BaseProvider):
    """No-LLM provider with generic LMView guidance."""

    def __init__(self) -> None:
        super().__init__(provider_name="none", model_name="lmview-none")

    async def generate_chat_completion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        start_ms = time.monotonic_ns() // 1_000_000
        user_message = ""
        for message in reversed(request.messages):
            if message.role == "user":
                user_message = message.content.strip()
                break

        content = (
            "LMView AI has no local or API model available right now. "
            "I can still give generic platform guidance: use the chart, indicators, "
            "order book, trades, market overview, news, alerts, and settings panels "
            "to inspect crypto market context. Live chart data in LMView is runtime "
            "data and may be newer than an LLM training cutoff.\n\n"
            f"Your request was: {user_message[:300] or 'No message provided.'}\n\n"
            "For market analysis, configure `AI_MODE=auto|local|api` with a healthy "
            "local endpoint or `DASHSCOPE_API_KEY`. This response is educational only "
            "and is not financial advice."
        )
        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        return LLMCompletionResponse(
            content=content,
            provider="none",
            model_name=self.model_name,
            is_mock=False,
            finish_reason="no_provider",
            token_input=self.estimate_tokens(user_message),
            token_output=self.estimate_tokens(content),
            latency_ms=elapsed_ms,
            metadata={"provider_type": "none"},
        )

    async def health_check(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(
            provider_name="none",
            is_healthy=True,
            latency_ms=0,
            model_loaded=True,
            checked_at=datetime.now(timezone.utc),
        )

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_name="none",
            provider_type=ProviderType.NONE,
            model_name=self.model_name,
            is_local=True,
            is_available=True,
            priority=999,
        )
