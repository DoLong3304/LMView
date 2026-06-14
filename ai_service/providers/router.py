"""Provider router for LMView AI.

Production-visible providers are `local`, `api`, and `none`.
`auto` is a mode, not a provider: it tries local, then API, then none.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from backend.models.ai.providers import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    ProviderHealthStatus,
    ProviderRoutingResult,
)
from ai_service.config import (
    AIProviderConfig,
    AISettings,
    get_api_key,
    list_available_api_models,
    load_settings,
)
from ai_service.providers.base import BaseProvider
from ai_service.providers.none_provider import NoneProvider
from backend.services.ai import metrics as ai_metrics

logger = logging.getLogger("ai_service.providers.router")

_router: Optional["ProviderRouter"] = None


class ProviderRouter:
    """Route completion requests to local, API, or none provider."""

    def __init__(self, settings: Optional[AISettings] = None) -> None:
        self.settings = settings or load_settings()
        self._providers: Dict[str, BaseProvider] = {"none": NoneProvider()}
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._register_local_provider()
        self._register_api_provider()

        # Register providers in the health monitor (except 'none')
        from ai_service.providers.health import get_health_monitor
        monitor = get_health_monitor()
        for name in self._providers:
            if name != "none":
                monitor.register(name)

        logger.info(
            "AI provider router initialized: mode=%s providers=%s config=%s",
            self.settings.mode,
            sorted(self._providers),
            self.settings.config_path,
        )

    def _provider_rows(self, public_name: str) -> List[AIProviderConfig]:
        return [p for p in self.settings.providers if p.name == public_name]

    def _register_local_provider(self) -> None:
        if self.settings.mode not in {"auto", "local"}:
            return
        rows = self._provider_rows("local")
        if not rows:
            return
        row = rows[0]
        try:
            from ai_service.providers.litellm_provider import LiteLLMProvider
        except ImportError:
            logger.info("litellm not installed; local provider unavailable")
            return

        model = row.model if row.model.startswith("openai/") else f"openai/{row.model}"
        self._providers["local"] = LiteLLMProvider(
            provider_name="local",
            model_name=model,
            base_url=row.base_url,
            api_key="not-needed",
            is_local=True,
            priority=row.priority,
        )

    def _register_api_provider(self) -> None:
        if self.settings.mode not in {"auto", "api"}:
            return
        rows = self._provider_rows("api")
        try:
            from ai_service.providers.litellm_provider import LiteLLMProvider
        except ImportError:
            logger.info("litellm not installed; API provider unavailable")
            return

        for row in rows:
            api_key = get_api_key(row.env_key)
            if not api_key:
                continue
            self._providers["api"] = LiteLLMProvider(
                provider_name="api",
                model_name=row.model,
                base_url=row.base_url,
                api_key=api_key,
                is_local=False,
                priority=row.priority,
            )
            break

    def get_provider_order(self) -> List[str]:
        """Return public provider names in try order."""
        mode = self.settings.mode
        if mode == "local":
            return ["local", "none"]
        if mode == "api":
            return ["api", "none"]
        if mode == "none":
            return ["none"]
        return ["local", "api", "none"]

    async def route_completion(
        self,
        request: LLMCompletionRequest,
    ) -> tuple[LLMCompletionResponse, ProviderRoutingResult]:
        self.initialize()
        providers_tried: List[str] = []
        providers_failed: List[str] = []

        # Record the configured mode for dashboards that want to know which
        # providers the router is *configured* to use (B13 observability).
        ai_metrics.record_provider_mode_active(self.settings.mode)

        # Get health monitor instance
        from ai_service.providers.health import get_health_monitor
        monitor = get_health_monitor()

        chain_depth = 0
        last_error: Optional[str] = None
        chain_start = time.monotonic()

        for provider_name in self.get_provider_order():
            # Skip if circuit breaker is open (for non-none providers)
            if provider_name != "none" and not monitor.should_try(provider_name):
                logger.warning("Skipping AI provider '%s' due to open circuit breaker", provider_name)
                providers_failed.append(provider_name)
                continue

            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            providers_tried.append(provider_name)
            chain_depth += 1
            provider_start = time.monotonic()
            try:
                response = await provider.generate_chat_completion(request)
                provider_duration = time.monotonic() - provider_start
                latency_ms = int(provider_duration * 1000)

                # Record success in health monitor
                monitor.record_success(provider_name, latency_ms=latency_ms)

                # Provider request success (B13 metrics).
                ai_metrics.record_provider_request(
                    provider=provider_name,
                    status="success",
                    duration_sec=provider_duration,
                )

                routing = ProviderRoutingResult(
                    selected_provider=provider_name,
                    selected_model=response.model_name,
                    is_local=provider.get_info().is_local,
                    is_mock=False,
                    fallback_used=len(providers_tried) > 1,
                    providers_tried=providers_tried,
                    providers_failed=providers_failed,
                    routing_reason=f"Selected {provider_name}",
                )
                return response, routing
            except Exception as exc:
                provider_duration = time.monotonic() - provider_start
                last_error = str(exc)[:200]
                providers_failed.append(provider_name)

                # Record failure in health monitor
                monitor.record_failure(provider_name)

                # Provider request failure (B13 metrics).
                ai_metrics.record_provider_request(
                    provider=provider_name,
                    status="failure",
                    duration_sec=provider_duration,
                )
                logger.warning("AI provider %s failed: %s", provider_name, last_error)

        # Record chain depth even when all providers failed.
        ai_metrics.record_provider_chain_depth(chain_depth, status="exhausted")

        none_provider = self._providers["none"]
        response = await none_provider.generate_chat_completion(request)
        routing = ProviderRoutingResult(
            selected_provider="none",
            selected_model=response.model_name,
            is_local=True,
            is_mock=False,
            fallback_used=True,
            providers_tried=providers_tried + ["none"],
            providers_failed=providers_failed,
            routing_reason="No local/API provider available; using generic none provider",
        )
        return response, routing

    async def health_check_all(self) -> Dict[str, ProviderHealthStatus]:
        self.initialize()
        results: Dict[str, ProviderHealthStatus] = {}
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
        self.initialize()
        return sorted(self._providers)

    def get_available_api_models(self) -> List[str]:
        return list_available_api_models(self.settings)


def get_provider_router() -> ProviderRouter:
    """Get singleton provider router."""
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router


def reset_provider_router() -> None:
    """Reset singleton for tests."""
    global _router
    _router = None
