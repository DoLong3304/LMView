"""
LiteLLM provider — unified interface to multiple LLM APIs.

Uses LiteLLM's OpenAI-compatible API to route requests to any configured model:
- OpenAI (GPT-4, etc.)
- Anthropic (Claude)
- Google (Gemini)
- DeepSeek
- Qwen API
- Llama API
- Local vLLM endpoints
- Any OpenAI-compatible endpoint

Does not hardcode API keys. Keys come from environment variables read by LiteLLM.
"""
from __future__ import annotations

import logging
import os
import time
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

logger = logging.getLogger("backend.services.ai.litellm_provider")


class LiteLLMProvider(BaseProvider):
    """LiteLLM-based provider for online API models."""

    def __init__(
        self,
        provider_name: str = "litellm",
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        is_local: bool = False,
        priority: int = 10,
    ):
        super().__init__(provider_name=provider_name, model_name=model_name)
        self.base_url = base_url or os.environ.get("LITELLM_BASE_URL", "http://litellm:4000")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", "")
        self.is_local = is_local
        self.priority = priority
        self._litellm = None

    def _get_litellm(self):
        """Lazy import litellm to avoid import errors when not installed."""
        if self._litellm is None:
            try:
                import litellm  # type: ignore
                self._litellm = litellm
            except ImportError:
                logger.warning("litellm not installed — install with: pip install litellm")
                raise
        return self._litellm

    async def generate_chat_completion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        """Generate completion via LiteLLM."""
        litellm = self._get_litellm()

        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        model = request.model or self.model_name

        if not model:
            raise ValueError(f"No model specified for provider {self.provider_name}")

        start_ms = time.monotonic_ns() // 1_000_000

        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
            }

            if self.base_url:
                kwargs["api_base"] = self.base_url
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if request.stop:
                kwargs["stop"] = request.stop  # type: ignore

            response = await litellm.acompletion(**kwargs)

            elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)

            return LLMCompletionResponse(
                content=content,
                provider=self.provider_name,
                model_name=model,
                is_mock=False,
                finish_reason=getattr(response.choices[0], "finish_reason", "stop"),
                token_input=usage.prompt_tokens if usage else None,
                token_output=usage.completion_tokens if usage else None,
                latency_ms=elapsed_ms,
                metadata={"provider_type": "litellm"},
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "LiteLLM completion failed for %s/%s: %s",
                self.provider_name, model, exc,
            )
            raise

    async def health_check(self) -> ProviderHealthStatus:
        """Check provider health by attempting a minimal completion."""
        start_ms = time.monotonic_ns() // 1_000_000
        try:
            litellm = self._get_litellm()
            model = self.model_name
            if not model:
                return ProviderHealthStatus(
                    provider_name=self.provider_name,
                    is_healthy=False,
                    error="No model configured",
                    checked_at=datetime.now(timezone.utc),
                )

            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
                "temperature": 0,
            }
            if self.base_url:
                kwargs["api_base"] = self.base_url
            if self.api_key:
                kwargs["api_key"] = self.api_key

            response = await litellm.acompletion(**kwargs)
            elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            return ProviderHealthStatus(
                provider_name=self.provider_name,
                is_healthy=True,
                latency_ms=elapsed_ms,
                model_loaded=True,
                checked_at=datetime.now(timezone.utc),
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            return ProviderHealthStatus(
                provider_name=self.provider_name,
                is_healthy=False,
                latency_ms=elapsed_ms,
                error=str(exc)[:200],
                checked_at=datetime.now(timezone.utc),
            )

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_name=self.provider_name,
            provider_type=ProviderType.LITELLM,
            model_name=self.model_name,
            is_local=self.is_local,
            is_available=True,  # availability confirmed by health_check
            priority=self.priority,
            base_url=self.base_url,
        )
