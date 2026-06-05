"""
Provider router — selects and routes LLM requests to the best available provider.

Provider priority is configurable. The router tries providers in order and falls
back to the next provider on failure. Mock is always available as final fallback.

Configuration modes:
- mock:  deterministic mock responses only
- api:   prefer online API providers (qwen_api → llama_api → mock)
- local: prefer local vLLM (local_vllm → qwen_api → llama_api → mock)
- auto:  try local first, then api, then mock (default production mode)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional

from backend.core.config import (
    AI_ENABLE_PROVIDER_FALLBACK,
    AI_ENABLE_REAL_LLM,
    AI_MODE,
    AI_PROVIDER_ORDER,
    AI_TEST_PROVIDER_ORDER,
    LITELLM_BASE_URL,
    LITELLM_MASTER_KEY,
    VLLM_BASE_URL,
    VLLM_MODEL,
)
from backend.models.ai.providers import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    ProviderHealthStatus,
    ProviderRoutingResult,
)
from backend.services.ai.base_provider import BaseProvider
from backend.services.ai.mock_provider import MockProvider

logger = logging.getLogger("backend.services.ai.provider_router")

# Singleton instance
_router: Optional["ProviderRouter"] = None


class ProviderRouter:
    """Routes LLM requests to the best available provider."""

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._mock = MockProvider()
        self._providers["mock"] = self._mock
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize configured providers based on environment.

        Called lazily on first request. Does not require all providers to
        be configured — the system starts with only mock mode available.
        """
        if self._initialized:
            return

        self._initialized = True

        if AI_MODE == "mock":
            logger.info("AI_MODE=mock — only mock provider enabled")
            return

        if not AI_ENABLE_REAL_LLM:
            logger.info("AI_ENABLE_REAL_LLM=false — only mock provider enabled")
            return

        # Try to register LiteLLM-based providers
        self._register_litellm_providers()

        # Try to register local vLLM provider
        self._register_vllm_provider()

        available = [n for n, p in self._providers.items() if n != "mock"]
        logger.info(
            "Provider router initialized: mode=%s, providers=%s",
            AI_MODE, available or ["mock only"],
        )

    def _register_litellm_providers(self) -> None:
        """Register LiteLLM-based API providers if keys are available."""
        try:
            from backend.services.ai.litellm_provider import LiteLLMProvider
        except ImportError:
            logger.info("litellm not installed — API providers unavailable")
            return

        # Qwen API
        qwen_key = os.environ.get("QWEN_API_KEY", "")
        if qwen_key:
            self._providers["qwen_api"] = LiteLLMProvider(
                provider_name="qwen_api",
                model_name="openai/qwen-plus",
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                api_key=qwen_key,
                priority=10,
            )
            logger.info("Registered qwen_api provider")

        # Llama API
        llama_key = os.environ.get("LLAMA_API_KEY", "")
        if llama_key:
            self._providers["llama_api"] = LiteLLMProvider(
                provider_name="llama_api",
                model_name="openai/Llama-4-Maverick-17B-128E-Instruct-FP8",
                base_url="https://api.llama.com/compat/v1",
                api_key=llama_key,
                priority=20,
            )
            logger.info("Registered llama_api provider")

        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            self._providers["openai"] = LiteLLMProvider(
                provider_name="openai",
                model_name="gpt-4o-mini",
                api_key=openai_key,
                priority=30,
            )
            logger.info("Registered openai provider")

        # Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if gemini_key:
            self._providers["gemini"] = LiteLLMProvider(
                provider_name="gemini",
                model_name="gemini/gemini-2.0-flash",
                api_key=gemini_key,
                priority=35,
            )
            logger.info("Registered gemini provider")

        # DeepSeek
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            self._providers["deepseek"] = LiteLLMProvider(
                provider_name="deepseek",
                model_name="openai/deepseek-chat",
                base_url="https://api.deepseek.com/v1",
                api_key=deepseek_key,
                priority=40,
            )
            logger.info("Registered deepseek provider")

        # LiteLLM proxy (for users running their own LiteLLM proxy)
        if LITELLM_MASTER_KEY:
            self._providers["litellm_proxy"] = LiteLLMProvider(
                provider_name="litellm_proxy",
                model_name=os.environ.get("LITELLM_DEFAULT_MODEL", ""),
                base_url=LITELLM_BASE_URL,
                api_key=LITELLM_MASTER_KEY,
                priority=50,
            )
            logger.info("Registered litellm_proxy provider")

    def _register_vllm_provider(self) -> None:
        """Register local vLLM provider if base URL and model are configured."""
        if not VLLM_MODEL:
            return

        try:
            from backend.services.ai.litellm_provider import LiteLLMProvider
        except ImportError:
            logger.info("litellm not installed — vLLM provider unavailable")
            return

        self._providers["local_vllm"] = LiteLLMProvider(
            provider_name="local_vllm",
            model_name=f"openai/{VLLM_MODEL}",
            base_url=VLLM_BASE_URL,
            api_key="not-needed",  # vLLM doesn't require API key
            is_local=True,
            priority=5,  # highest priority when in local-first mode
        )
        logger.info("Registered local_vllm provider: %s", VLLM_MODEL)

    def _get_provider_order(self) -> List[str]:
        """Get provider order based on AI_MODE."""
        if AI_MODE == "mock":
            return ["mock"]
        elif AI_MODE == "api":
            return [p.strip() for p in AI_TEST_PROVIDER_ORDER if p.strip()]
        elif AI_MODE == "local":
            return [p.strip() for p in AI_PROVIDER_ORDER if p.strip()]
        else:  # auto
            return [p.strip() for p in AI_PROVIDER_ORDER if p.strip()]

    async def route_completion(
        self,
        request: LLMCompletionRequest,
    ) -> tuple[LLMCompletionResponse, ProviderRoutingResult]:
        """
        Route a completion request to the best available provider.

        Returns:
            Tuple of (LLM response, routing metadata).
        """
        self.initialize()

        provider_order = self._get_provider_order()
        providers_tried: List[str] = []
        providers_failed: List[str] = []

        for provider_name in provider_order:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue

            providers_tried.append(provider_name)

            try:
                response = await provider.generate_chat_completion(request)

                routing = ProviderRoutingResult(
                    selected_provider=provider_name,
                    selected_model=response.model_name,
                    is_local=provider.get_info().is_local,
                    is_mock=response.is_mock,
                    fallback_used=len(providers_tried) > 1,
                    providers_tried=providers_tried,
                    providers_failed=providers_failed,
                    routing_reason=f"Selected {provider_name} (priority order)",
                )

                return response, routing

            except Exception as exc:
                providers_failed.append(provider_name)
                logger.warning(
                    "Provider %s failed: %s — trying next",
                    provider_name, str(exc)[:200],
                )

                if not AI_ENABLE_PROVIDER_FALLBACK:
                    break

        # All providers failed — use mock
        logger.warning("All providers failed — falling back to mock")
        response = await self._mock.generate_chat_completion(request)

        routing = ProviderRoutingResult(
            selected_provider="mock",
            selected_model="phase0_mock",
            is_local=True,
            is_mock=True,
            fallback_used=True,
            providers_tried=providers_tried + ["mock"],
            providers_failed=providers_failed,
            routing_reason="All configured providers failed — mock fallback",
        )

        return response, routing

    async def health_check_all(self) -> Dict[str, ProviderHealthStatus]:
        """Run health checks on all registered providers."""
        self.initialize()
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception as exc:
                results[name] = ProviderHealthStatus(
                    provider_name=name,
                    is_healthy=False,
                    error=str(exc)[:200],
                )
        return results

    def get_available_providers(self) -> List[str]:
        """Return names of all registered providers."""
        self.initialize()
        return list(self._providers.keys())


def get_provider_router() -> ProviderRouter:
    """Get or create the singleton provider router."""
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router
