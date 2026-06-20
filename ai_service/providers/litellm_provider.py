"""LiteLLM provider for local and API OpenAI-compatible endpoints."""
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
from ai_service.providers.base import BaseProvider
from ai_service.config import get_api_keys, rotate_api_key, get_current_api_key

logger = logging.getLogger("ai_service.providers.litellm_provider")


class QuotaExhaustedError(Exception):
    """Raised when all API keys for a provider/model are exhausted."""
    pass


class LiteLLMProvider(BaseProvider):
    """LiteLLM-based provider for online API models with model fallback chain.

    Supports multiple models in priority order. If the primary model
    exhausts quota, the next model in the chain is tried automatically.
    """

    def __init__(
        self,
        provider_name: str = "litellm",
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        is_local: bool = False,
        priority: int = 10,
        fallback_models: Optional[list] = None,
    ):
        super().__init__(provider_name=provider_name, model_name=model_name)
        self.base_url = base_url or os.environ.get("LITELLM_BASE_URL", "http://litellm:4000")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", "")
        self.is_local = is_local
        self.priority = priority
        self.fallback_models = fallback_models or []
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

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        """Check if an exception indicates quota exhaustion or rate limiting.

        Matches:
        - ``AllocationQuota.FreeTierOnly`` (Alibaba Cloud — free quota exhausted)
        - HTTP 429 (rate limit)
        - HTTP 401/402/403 with quota/exhausted wording
        - LiteLLM's built-in rate limit detection
        """
        msg = str(exc).lower()

        # Alibaba Cloud ModelStudio: free quota exhausted per model
        if "allocationquota" in msg or "freetieronly" in msg:
            return True

        # HTTP status code + keyword matching
        if any(code in msg for code in ["429", "401", "402", "403"]):
            if any(kw in msg for kw in ["quota", "exhaust", "rate", "limit", "insufficient", "token", "credit"]):
                return True

        # LiteLLM-specific rate limit
        if "rate_limit_error" in msg or "rate limit" in msg:
            return True

        # Content policy / safety violations are NOT quota errors
        if "content_filter" in msg or "safety" in msg:
            return False
        return False

    async def generate_chat_completion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        """Generate completion via LiteLLM with automatic key + model rotation.

        Fallback chain:
        1. Try primary model with current API key
        2. On quota error: rotate key and retry same model
        3. All keys exhausted for model: try next fallback model
        4. All models exhausted: raise ``QuotaExhaustedError``
        """
        litellm = self._get_litellm()
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        models_to_try = [self.model_name] + self.fallback_models if self.model_name else self.fallback_models
        if not models_to_try:
            raise ValueError(f"No model specified for provider {self.provider_name}")

        env_key = "DASHSCOPE_API_KEY"
        keys = get_api_keys(env_key) if not self.is_local else []

        last_error: Optional[Exception] = None

        for model_idx, model in enumerate(models_to_try):
            max_key_attempts = max(len(keys), 1) if not self.is_local else 1

            for key_attempt in range(max_key_attempts):
                start_ms = time.monotonic_ns() // 1_000_000

                try:
                    kwargs: dict = {
                        "model": model,
                        "messages": messages,
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens,
                        "top_p": request.top_p,
                    }

                    if self.base_url:
                        kwargs["api_base"] = self.base_url

                    active_key = get_current_api_key(env_key) if not self.is_local else self.api_key
                    if active_key:
                        kwargs["api_key"] = active_key
                    elif self.api_key:
                        kwargs["api_key"] = self.api_key

                    if request.stop:
                        kwargs["stop"] = request.stop

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
                        token_input=getattr(usage, "prompt_tokens", None),
                        token_output=getattr(usage, "completion_tokens", None),
                        latency_ms=elapsed_ms,
                        metadata={
                            "provider_type": "litellm",
                            "model_fallback_used": model_idx > 0,
                            "key_fallback_used": key_attempt > 0,
                            "usage": {
                                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                                "completion_tokens": getattr(usage, "completion_tokens", None),
                                "total_tokens": getattr(usage, "total_tokens", None),
                            },
                        },
                    )

                except Exception as exc:
                    last_error = exc
                    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

                    if self._is_quota_error(exc) and len(keys) > 1:
                        rotate_api_key(env_key)
                        logger.warning(
                            "Quota exhausted for %s — key %d/%d, rotating",
                            model, key_attempt + 1, max_key_attempts,
                        )
                        continue

                    if self._is_quota_error(exc):
                        logger.warning(
                            "All keys exhausted for %s — trying next model (%d/%d)",
                            model, model_idx + 1, len(models_to_try),
                        )
                        break  # All keys tried, move to next model

                    logger.error(
                        "LiteLLM completion failed for %s: %s",
                        model, exc,
                    )
                    raise

        # All models + keys exhausted
        raise QuotaExhaustedError(
            f"All models/keys exhausted for {self.provider_name}: "
            f"{models_to_try}"
        ) from last_error

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
            provider_type=ProviderType.LOCAL if self.is_local else ProviderType.API,
            model_name=self.model_name,
            is_local=self.is_local,
            is_available=True,  # availability confirmed by health_check
            priority=self.priority,
            base_url=self.base_url,
        )
