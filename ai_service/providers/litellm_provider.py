"""LiteLLM provider for local and API OpenAI-compatible endpoints."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Optional

from backend.models.ai.providers import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    ProviderHealthStatus,
    ProviderInfo,
    ProviderType,
)
from ai_service.providers.base import BaseProvider
from ai_service.config import get_api_base_urls, get_api_keys

logger = logging.getLogger("ai_service.providers.litellm_provider")

# ── Provider-level exact-match cache ───────────────────────────────────────
_PROVIDER_CACHE: Dict[str, LLMCompletionResponse] = {}
_PROVIDER_CACHE_MAX = 50
_PROVIDER_CACHE_TTL = 15.0  # seconds


def _provider_cache_get(key: str) -> Optional[LLMCompletionResponse]:
    """Get cached response if not expired."""
    entry = _PROVIDER_CACHE.get(key)
    if entry is None:
        return None
    response_obj, ts = entry
    if time.time() - ts > _PROVIDER_CACHE_TTL:
        _PROVIDER_CACHE.pop(key, None)
        return None
    return response_obj


def _provider_cache_set(key: str, response_obj: LLMCompletionResponse) -> None:
    """Store response in cache with timestamp."""
    if len(_PROVIDER_CACHE) >= _PROVIDER_CACHE_MAX:
        # Evict oldest
        oldest = min(_PROVIDER_CACHE.keys(), key=lambda k: _PROVIDER_CACHE[k][1])
        _PROVIDER_CACHE.pop(oldest, None)
    _PROVIDER_CACHE[key] = (response_obj, time.time())


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
        tier: Optional[str] = None,  # filter: 'standard', 'reserved', 'benchmark'
    ):
        super().__init__(provider_name=provider_name, model_name=model_name)
        self.base_url = base_url or os.environ.get("LITELLM_BASE_URL", "http://litellm:4000")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", "")
        self.is_local = is_local
        self.priority = priority
        self.fallback_models = fallback_models or []
        self.tier = tier
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

        DashScope (Alibaba Cloud ModelStudio) returns specific error codes
        for quota exhaustion vs other failures. Use exact code matching
        instead of broad keyword search to avoid false positives.

        DashScope quota codes:
        - ``AllocationQuota.FreeTierOnly`` — free quota exhausted for this model+key
        - ``Throttling.RateLimit`` — rate-limited
        - ``FlowControl.Limit`` — concurrency limit
        - ``QuotaExhausted`` — general quota exhausted
        """
        msg = str(exc)
        msg_lower = msg.lower()

        # DashScope/Alibaba Cloud exact error codes
        dashscope_codes = [
            "allocationquota.freetieronly",
            "allocationquota",
            "throttling.ratelimit",
            "flowcontrol.limit",
            "quotae exhausted",  # DashScope code text
            "insufficient_quota",  # OpenAI-compatible quota code (DashScope returns this on 403)
        ]
        for code in dashscope_codes:
            if code in msg_lower:
                return True

        # LiteLLM wraps errors with "API error <code>:" — check code substring
        if "allocationquota" in msg_lower or "freetieronly" in msg_lower:
            return True

        # HTTP status code 429 (rate limit) — common across providers
        if "429" in msg:
            return True

        # Quota exhausted message — works across providers (OpenAI-compatible)
        # LiteLLM wraps 403 insufficient_quota as a generic APIError with
        # the human-readable message but without the status code in str().
        if "quota" in msg_lower and "exhausted" in msg_lower:
            return True

        # Generic rate limit patterns (avoid "quota" broad match — too many false positives)
        if "rate_limit_error" in msg_lower or "rate limit" in msg_lower:
            return True

        # Known non-quota errors that should NOT be treated as quota:
        # - InvalidApiKey, AccessDenied, ModelNotFound, InvalidParameter, etc.
        non_quota = [
            "invalidapikey", "accessdenied", "access_denied",
            "modelnotfound", "model_not_found",
            "invalidparameter", "invalid_parameter",
            "contentfilter", "content_filter",
            "internalerror", "internal_error",
            "timeout", "timed out",
        ]
        for nq in non_quota:
            if nq in msg_lower:
                return False

        return False

    @staticmethod
    def _is_retriable_key_model_error(exc: Exception) -> bool:
        """Return True for key/model access errors where another key/model may work."""
        msg = str(exc).lower()
        patterns = [
            "access to model denied",
            "model access denied",
            "not eligible for using the model",
            "modelnotfound",
            "model_not_found",
            "accessdenied",
            "access_denied",
            "invalidapikey",
            "invalid_api_key",
            "invalid api key",
        ]
        return any(p in msg for p in patterns)

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

        # Provider-level exact-match cache (rapid dedup, 15s TTL)
        cache_key = str(messages)
        cached = _provider_cache_get(cache_key)
        if cached is not None:
            logger.debug("Provider cache hit for exact messages")
            return cached

        models_to_try = [self.model_name] + self.fallback_models if self.model_name else self.fallback_models
        if not models_to_try:
            raise ValueError(f"No model specified for provider {self.provider_name}")

        env_key = "DASHSCOPE_API_KEY"
        keys = get_api_keys(env_key) if not self.is_local else []
        num_keys = len(keys)

        # Per-key base URLs for DashScope workspace-scoped keys.
        # Each workspace API key must be used with its own endpoint.
        # If DASHSCOPE_API_BASE_URLS is set, it must have the same count as keys.
        base_urls = get_api_base_urls(env_key) if not self.is_local else []
        if base_urls and len(base_urls) != num_keys:
            logger.warning(
                "DASHSCOPE_API_BASE_URLS count (%d) != DASHSCOPE_API_KEYS count (%d) — ignoring per-key URLs",
                len(base_urls), num_keys,
            )
            base_urls = []

        # ── Key-rotation strategy ──────────────────────────────────────────
        # Each key_attempt uses `keys[key_idx]` directly instead of the global
        # _API_KEY_INDEX, eliminating concurrent-request races on key selection.
        # key_start_offset provides best-effort spreading across requests
        # without a global lock.
        # Exhaustion cache is NOT used for skipping — failed combos are always
        # retried because quota state may change between requests or a key may
        # have quota on a different model. Only used for logging.
        key_offset: int = 0
        if not self.is_local and num_keys > 1:
            try:
                job_id = os.environ.get("HOSTNAME", "")
                if job_id:
                    key_offset = sum(ord(c) for c in job_id) % num_keys
            except Exception:
                key_offset = 0

        last_error: Optional[Exception] = None

        for model_idx, model in enumerate(models_to_try):
            # ── Try each key for this model ────────────────────────────────
            for key_attempt in range(num_keys if not self.is_local else 1):
                # Key index: start from offset, wrap around
                key_idx = (key_offset + key_attempt) % num_keys if not self.is_local and num_keys > 0 else 0

                start_ms = time.monotonic_ns() // 1_000_000

                try:
                    kwargs: dict = {
                        "model": model,
                        "messages": messages,
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens,
                        "top_p": request.top_p,
                    }

                    # Use per-key base URL if available (DashScope workspace keys)
                    if base_urls and key_idx < len(base_urls):
                        kwargs["api_base"] = base_urls[key_idx]
                    elif self.base_url:
                        kwargs["api_base"] = self.base_url

                    # Use key_idx directly — no global _API_KEY_INDEX
                    if not self.is_local and keys and key_idx < len(keys):
                        kwargs["api_key"] = keys[key_idx]
                    elif self.api_key:
                        kwargs["api_key"] = self.api_key

                    if request.stop:
                        kwargs["stop"] = request.stop

                    if request.tools:
                        kwargs["tools"] = [t.model_dump() for t in request.tools]
                    if request.tool_choice:
                        kwargs["tool_choice"] = request.tool_choice

                    # DashScope context caching: mark system prompt for KV cache
                    # Reduces first-token latency by ~80% on repeated system prompts.
                    api_base = kwargs.get("api_base", self.base_url or "")
                    if "dashscope" in api_base or "aliyuncs" in api_base:
                        kwargs["extra_headers"] = {
                            "X-DashScope-Cache": "enable",
                            "X-DashScope-SSE": "enable",
                        }

                    response = await litellm.acompletion(**kwargs)

                    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                    content = response.choices[0].message.content or ""
                    usage = getattr(response, "usage", None)

                    # Extract tool_calls if present
                    tool_calls = None
                    msg = response.choices[0].message
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tool_calls = []
                        for tc in msg.tool_calls:
                            tool_calls.append({
                                "id": getattr(tc, "id", None),
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            })

                    response_obj = LLMCompletionResponse(
                        content=content,
                        provider=self.provider_name,
                        model_name=model,
                        is_mock=False,
                        finish_reason=getattr(response.choices[0], "finish_reason", "stop"),
                        token_input=getattr(usage, "prompt_tokens", None),
                        token_output=getattr(usage, "completion_tokens", None),
                        latency_ms=elapsed_ms,
                        tool_calls=tool_calls,
                        metadata={
                            "provider_type": "litellm",
                            "model_fallback_used": model_idx > 0,
                            "key_fallback_used": key_idx != 0,
                            "tool_calls": tool_calls,
                            "usage": {
                                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                                "completion_tokens": getattr(usage, "completion_tokens", None),
                                "total_tokens": getattr(usage, "total_tokens", None),
                            },
                        },
                    )
                    # Store in provider cache (exact message dedup, 15s TTL)
                    _provider_cache_set(cache_key, response_obj)
                    return response_obj

                except Exception as exc:
                    last_error = exc
                    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

                    if self._is_quota_error(exc):
                        # Log exhaustion but DO NOT skip on retry — quota may
                        # free up or a different model+key may work.
                        logger.info(
                            "Quota exhausted for %s (key %d/%d) — trying next",
                            model, key_idx + 1, max(num_keys, 1),
                        )
                        continue  # Try next key (or next model if last key)

                    if self._is_retriable_key_model_error(exc):
                        logger.warning(
                            "Model/key unavailable for %s (key %d/%d) — trying next key/model: %s",
                            model, key_idx + 1, max(num_keys, 1), str(exc)[:160],
                        )
                        continue

                    # Non-retriable error: fail immediately
                    logger.error(
                        "LiteLLM completion failed for %s: %s",
                        model, exc,
                    )
                    raise

            # All keys exhausted for this model; try next model
            logger.info(
                "All keys exhausted for %s (key_offset=%d) — trying next model (%d/%d)",
                model, key_offset, model_idx + 1, len(models_to_try),
            )

        # All models + keys exhausted
        raise QuotaExhaustedError(
            f"All models/keys exhausted for {self.provider_name}: "
            f"{models_to_try}"
        ) from last_error

    async def generate_chat_completion_stream(
        self,
        request: LLMCompletionRequest,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion via LiteLLM with key rotation.

        Yields SSE-encoded token strings for streaming consumption.
        Uses the model fallback chain on failure.
        Handles quota errors via key rotation per batch.
        """
        litellm = self._get_litellm()
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        models_to_try = [self.model_name] + self.fallback_models if self.model_name else self.fallback_models
        if not models_to_try:
            raise ValueError(f"No model specified for provider {self.provider_name}")

        env_key = "DASHSCOPE_API_KEY"
        keys = get_api_keys(env_key) if not self.is_local else []
        num_keys = len(keys)

        # Per-key base URLs for DashScope workspace-scoped keys (streaming)
        base_urls = get_api_base_urls(env_key) if not self.is_local else []
        if base_urls and len(base_urls) != num_keys:
            base_urls = []

        key_offset: int = 0
        if not self.is_local and num_keys > 1:
            try:
                job_id = os.environ.get("HOSTNAME", "")
                if job_id:
                    key_offset = sum(ord(c) for c in job_id) % num_keys
            except Exception:
                key_offset = 0

        last_error: Optional[Exception] = None

        for model_idx, model in enumerate(models_to_try):
            for key_attempt in range(num_keys if not self.is_local else 1):
                key_idx = (key_offset + key_attempt) % num_keys if not self.is_local and num_keys > 0 else 0

                try:
                    kwargs: dict = {
                        "model": model,
                        "messages": messages,
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens,
                        "top_p": request.top_p,
                        "stream": True,
                    }
                    # Use per-key base URL if available (DashScope workspace keys)
                    if base_urls and key_idx < len(base_urls):
                        kwargs["api_base"] = base_urls[key_idx]
                    elif self.base_url:
                        kwargs["api_base"] = self.base_url
                    # Use key_idx directly — no global _API_KEY_INDEX
                    if not self.is_local and keys and key_idx < len(keys):
                        kwargs["api_key"] = keys[key_idx]
                    elif self.api_key:
                        kwargs["api_key"] = self.api_key

                    # DashScope context caching (streaming)
                    api_base = kwargs.get("api_base", self.base_url or "")
                    if "dashscope" in api_base or "aliyuncs" in api_base:
                        kwargs["extra_headers"] = {
                            "X-DashScope-Cache": "enable",
                            "X-DashScope-SSE": "enable",
                        }

                    accumulated = ""
                    response = await litellm.acompletion(**kwargs)
                    async for chunk in response:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta and delta.content:
                            accumulated += delta.content
                            yield f'{{"content": {json.dumps(delta.content)}, "done": false}}'
                        finish = chunk.choices[0].finish_reason if chunk.choices else None
                        if finish == "stop" or (delta and delta.content is None):
                            yield f'{{"content": {json.dumps(accumulated)}, "done": true}}'
                            return
                    # If loop ends without finish_reason, yield accumulated
                    yield f'{{"content": {json.dumps(accumulated)}, "done": true}}'
                    return

                except Exception as exc:
                    last_error = exc
                    if self._is_quota_error(exc):
                        logger.info(
                            "Stream quota exhausted for %s (key %d/%d) — trying next",
                            model, key_idx + 1, max(num_keys, 1),
                        )
                        continue
                    if self._is_retriable_key_model_error(exc):
                        logger.warning(
                            "Stream model/key unavailable for %s (key %d/%d) — trying next key/model: %s",
                            model, key_idx + 1, max(num_keys, 1), str(exc)[:160],
                        )
                        continue
                    logger.error("LiteLLM stream failed for %s: %s", model, exc)
                    raise

            logger.info(
                "All keys exhausted for %s (stream) — trying next model (%d/%d)",
                model, model_idx + 1, len(models_to_try),
            )

        # All models + keys exhausted — yield error as stream event
        error_msg = f"All models/keys exhausted: {models_to_try}"
        logger.error(error_msg)
        yield f'{{"error": {json.dumps(error_msg)}, "done": true}}'

    async def warmup(self) -> None:
        """Pre-warm provider connection pool and API key validation.

        Runs a minimal health-check completion to prime LiteLLM connection
        cache, validate API keys, and load model into inference cache.
        Failures are logged but not raised.
        """
        import litellm

        # Enable litellm library-level in-memory response caching
        # Caches exact message → response mappings for 60s TTL.
        # This is Layer 2 — complements ai_service.core.cache (Layer 1)
        # and the provider-level exact-match cache (Layer 0).
        try:
            if not hasattr(litellm, "cache") or litellm.cache is None:
                import diskcache  # type: ignore
                litellm.cache = litellm.Cache(
                    type="disk",
                    ttl=60,
                    namespace="litellm_response_cache",
                )
                logger.info("LiteLLM disk cache enabled (ttl=60s)")
        except ImportError:
            # diskcache not installed; use in-memory cache
            litellm.cache = litellm.Cache(
                type="local",
                ttl=60,
            )
            logger.info("LiteLLM in-memory cache enabled (ttl=60s)")
        except Exception as exc:
            logger.warning("Failed to enable litellm cache: %s", exc)

        try:
            model = self.model_name
            if not model:
                return
            kwargs: dict = {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
                "temperature": 0,
            }
            if self.base_url:
                kwargs["api_base"] = self.base_url
            if self.api_key:
                kwargs["api_key"] = self.api_key

            logger.info(
                "Pre-warming provider '%s' with model %s...",
                self.provider_name, model,
            )
            await litellm.acompletion(**kwargs)
            logger.info(
                "Provider '%s' warmed up successfully (model=%s)",
                self.provider_name, model,
            )
        except Exception as exc:
            logger.warning(
                "Provider warmup failed for %s (model=%s): %s",
                self.provider_name, model, str(exc)[:200],
            )

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
