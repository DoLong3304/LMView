"""Provider router for LMView AI.

Production-visible providers are `local`, `api`, and `none`.
`auto` is a mode, not a provider: it tries local, then API, then none.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

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
    list_models_by_tier,
    load_settings,
)
from ai_service.providers.base import BaseProvider
from ai_service.providers.none_provider import NoneProvider
from ai_service.providers.litellm_provider import QuotaExhaustedError
from backend.services.ai import metrics as ai_metrics

logger = logging.getLogger("ai_service.providers.router")

_router: Optional["ProviderRouter"] = None


class ProviderRouter:
    """Route completion requests to local, API, or none provider."""

    def __init__(self, settings: Optional[AISettings] = None) -> None:
        self.settings = settings or load_settings()
        self._providers: Dict[str, BaseProvider] = {"none": NoneProvider()}
        self._api_config_rows: List[AIProviderConfig] = []  # keep for tier filtering
        self._initialized = False
        self._all_exhausted_since: float = 0.0  # timestamp when all models+keys exhausted

    def _is_all_exhausted(self) -> bool:
        """Check if all providers were recently fully exhausted (300s cooldown)."""
        if self._all_exhausted_since == 0.0:
            return False
        return (time.monotonic() - self._all_exhausted_since) < 300.0

    def probe_exhaustion(self) -> bool:
        """Quickly probe if ALL API providers are exhausted.

        Makes a single minimal LLM call. If it fails with quota exhaustion,
        marks all providers as exhausted (avoiding 38-combo loop on first query).
        Returns True if all providers are exhausted, False otherwise.
        """
        if self._is_all_exhausted():
            return True
        if not self._providers or "api" not in self._providers:
            return False
        provider = self._providers.get("api")
        if not provider or not hasattr(provider, "generate_chat_completion"):
            return False
        try:
            import asyncio
            from ai_service.providers.litellm_provider import QuotaExhaustedError
            from ai_service.agents.types import LLMMessage, LLMCompletionRequest

            probe_req = LLMCompletionRequest(
                messages=[LLMMessage(role="user", content="ping")],
                max_tokens=5,
                temperature=0.0,
            )
            asyncio.get_event_loop().run_until_complete(
                asyncio.wait_for(
                    provider.generate_chat_completion(probe_req),
                    timeout=10.0,
                )
            )
            return False
        except QuotaExhaustedError:
            self._all_exhausted_since = time.monotonic()
            return True
        except Exception:
            return False

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

        if not rows:
            return

        # Store all API config rows for tier-filtered runtime selection
        self._api_config_rows = rows

        # Build the catch-all provider with all available models (no tier filter)
        # Used when selected_tier is None (i.e. user didn't request a specific tier).
        # When selected_tier is set, route_completion builds a filtered provider.
        primary = rows[0]
        api_key = get_api_key(primary.env_key)
        if not api_key:
            return

        fallback_models = []
        for fb_row in rows[1:]:
            fb_key = get_api_key(fb_row.env_key)
            if fb_key:
                fallback_models.append(fb_row.model)

        self._providers["api"] = LiteLLMProvider(
            provider_name="api",
            model_name=primary.model,
            base_url=primary.base_url,
            api_key=api_key,
            is_local=False,
            priority=primary.priority,
            fallback_models=fallback_models,
        )

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
        selected_model: Optional[str] = None,
        selected_tier: Optional[str] = None,
    ) -> tuple[LLMCompletionResponse, ProviderRoutingResult]:
        """Route completion request to the best available provider.

        Args:
            request: The LLM completion request.
            selected_model: Force a specific model (e.g. 'qwen3.7-plus').
                           Overrides tier selection. None = use rotation.
            selected_tier: Model tier filter: 'standard', 'reserved', 'benchmark'.
                          None = use all tiers for rotation.
        """
        self.initialize()
        providers_tried: List[str] = []
        providers_failed: List[str] = []

        ai_metrics.record_provider_mode_active(self.settings.mode)
        chain_depth = 0

        from ai_service.providers.health import get_health_monitor
        from ai_service.providers.litellm_provider import QuotaExhaustedError
        monitor = get_health_monitor()

        # Fast-path: if all providers were recently fully exhausted, skip to none.
        # Prevents 8s+ stall when all 38 model+key combos fail with the same
        # AllocationQuota.FreeTierOnly error.
        if self._is_all_exhausted():
            logger.info("All providers exhausted within last 300s — skipping API calls")
            none_provider = self._providers["none"]
            response = await none_provider.generate_chat_completion(request)
            routing = ProviderRoutingResult(
                selected_provider="none",
                selected_model="lmview-none",
                is_local=False,
                is_mock=False,
                fallback_used=True,
                providers_tried=["all_exhausted_fast_path"],
                providers_failed=[],
                routing_reason="All providers exhausted within last 300s — fast path skip",
            )
            ai_metrics.record_provider_chain_depth(0, status="exhausted_skip")
            return response, routing

        # If a specific model is requested, find it in the provider config
        # and create a dedicated provider for this request
        if selected_model:
            provider = self._build_model_provider(selected_model, selected_tier)
            if provider:
                try:
                    provider_start = time.monotonic()
                    response = await provider.generate_chat_completion(request)
                    provider_duration = time.monotonic() - provider_start
                    latency_ms = int(provider_duration * 1000)
                    routing = ProviderRoutingResult(
                        selected_provider=provider.provider_name,
                        selected_model=selected_model,
                        is_local=False,
                        is_mock=False,
                        fallback_used=False,
                        providers_tried=[provider.provider_name],
                        providers_failed=[],
                        routing_reason=f"User-selected model: {selected_model}",
                    )
                    return response, routing
                except Exception as exc:
                    logger.warning(
                        "User-selected model %s failed: %s — falling back to rotation",
                        selected_model, str(exc)[:200],
                    )
                    # Fall through to normal rotation

        # If a specific tier is requested, build a tier-filtered provider
        # that only contains models from that tier. This prevents reserved
        # or benchmark models from being burned on standard-tier tasks.
        # If a specific tier is requested, try all tiers in cascade order:
        #   selected_tier → remaining_tiers → catch-all api
        # This ensures we don't give up after one tier is exhausted
        # when another tier's models could still handle the request.
        if selected_tier and not selected_model:
            _TIER_CASCADE = ["standard", "reserved", "benchmark"]
            tier_order = [selected_tier] + [t for t in _TIER_CASCADE if t != selected_tier]

            for cascade_tier in tier_order:
                tier_provider = self._build_tier_provider(cascade_tier)
                if not tier_provider:
                    continue
                tier_name = tier_provider.provider_name
                providers_tried.append(tier_name)
                chain_depth += 1
                provider_start = time.monotonic()
                try:
                    response = await tier_provider.generate_chat_completion(request)
                    provider_duration = time.monotonic() - provider_start
                    latency_ms = int(provider_duration * 1000)

                    monitor.record_success(tier_name, latency_ms=latency_ms)
                    ai_metrics.record_provider_request(
                        provider=tier_name,
                        status="success",
                        duration_sec=provider_duration,
                    )

                    routing = ProviderRoutingResult(
                        selected_provider=tier_name,
                        selected_model=response.model_name,
                        is_local=False,
                        is_mock=False,
                        fallback_used=len(providers_tried) > 1,
                        providers_tried=providers_tried,
                        providers_failed=providers_failed,
                        routing_reason=f"Selected tier: {cascade_tier} (cascade from {selected_tier})",
                    )
                    return response, routing
                except QuotaExhaustedError as exc:
                    provider_duration = time.monotonic() - provider_start
                    last_error = str(exc)[:200]
                    providers_failed.append(tier_name)
                    ai_metrics.record_provider_request(
                        provider=tier_name,
                        status="quota_exhausted",
                        duration_sec=provider_duration,
                    )
                    logger.warning(
                        "Tier provider %s (%s) exhausted — cascade to next tier",
                        tier_name, cascade_tier,
                    )
                    continue
                except Exception as exc:
                    provider_duration = time.monotonic() - provider_start
                    last_error = str(exc)[:200]
                    providers_failed.append(tier_name)
                    monitor.record_failure(tier_name)
                    ai_metrics.record_provider_request(
                        provider=tier_name,
                        status="failure",
                        duration_sec=provider_duration,
                    )
                    logger.warning(
                        "Tier provider %s failed: %s — cascade to next tier",
                        tier_name, last_error,
                    )
                    continue
            logger.warning("All tiers exhausted (cascade from %s) — falling through to catch-all", selected_tier)

        last_error: Optional[str] = None

        for provider_name in self.get_provider_order():
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

                monitor.record_success(provider_name, latency_ms=latency_ms)
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

            except QuotaExhaustedError as exc:
                # All models + keys exhausted for this provider; move to next
                provider_duration = time.monotonic() - provider_start
                last_error = str(exc)[:200]
                providers_failed.append(provider_name)
                # Don't open circuit breaker for quota exhaustion — key may rotate
                # Only record metrics without marking unhealthy
                ai_metrics.record_provider_request(
                    provider=provider_name,
                    status="quota_exhausted",
                    duration_sec=provider_duration,
                )
                logger.warning(
                    "AI provider %s fully exhausted (all models/keys), falling through: %s",
                    provider_name, last_error,
                )
                continue

            except asyncio.CancelledError:
                # Graph-level asyncio.wait_for timed out while we were trying
                # LLM calls. Mark all providers as exhausted so subsequent
                # requests use the fast-path (avoids re-trying all 38 combos).
                # This is safe because CancelledError only fires during an
                # LLM call (all of which fail the same way when keys exhausted).
                self._all_exhausted_since = time.monotonic()
                raise

            except Exception as exc:
                provider_duration = time.monotonic() - provider_start
                last_error = str(exc)[:200]
                providers_failed.append(provider_name)
                monitor.record_failure(provider_name)
                ai_metrics.record_provider_request(
                    provider=provider_name,
                    status="failure",
                    duration_sec=provider_duration,
                )
                logger.warning("AI provider %s failed: %s", provider_name, last_error)

        # Mark all providers as exhausted so subsequent requests skip fast-path.
        # This MUST be set even if the coroutine is cancelled (CancelledError
        # from graph-level asyncio.wait_for) — otherwise every first request
        # after restart suffers through all 38 model+key combos.
        self._all_exhausted_since = time.monotonic()

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

    async def route_completion_stream(
        self,
        request: LLMCompletionRequest,
        selected_model: Optional[str] = None,
        selected_tier: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Route a streaming completion request.

        Yields SSE-encoded token strings from the first healthy provider.
        Falls through providers on failure.

        If ``selected_model`` is set, tries that model directly first.
        """
        self.initialize()
        providers_tried: List[str] = []
        streamed = False

        from ai_service.providers.health import get_health_monitor
        monitor = get_health_monitor()

        # Try user-selected model first
        if selected_model:
            provider = self._build_model_provider(selected_model, selected_tier)
            if provider:
                logger.info("Streaming using user-selected model: %s", selected_model)
                try:
                    async for event in provider.generate_chat_completion_stream(request):
                        yield event
                        streamed = True
                    if streamed:
                        return
                except Exception as exc:
                    logger.warning(
                        "User-selected model %s stream failed: %s — falling back",
                        selected_model, str(exc)[:200],
                    )

        for provider_name in self.get_provider_order():
            if provider_name != "none" and not monitor.should_try(provider_name):
                logger.warning("Skipping AI provider '%s' for stream (circuit breaker)", provider_name)
                providers_tried.append(provider_name)
                continue

            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            providers_tried.append(provider_name)

            try:
                async for event in provider.generate_chat_completion_stream(request):
                    yield event
                    streamed = True
                if streamed:
                    return
            except Exception as exc:
                logger.warning("Stream provider %s failed: %s", provider_name, exc)
                monitor.record_failure(provider_name)
                continue

        # All providers exhausted — yield error event
        yield '{"error": "All AI providers unavailable for streaming", "done": true}'

    async def warmup_all(self) -> None:
        """Pre-warm all registered providers on startup.

        Called once during FastAPI lifespan startup to prime provider
        connection pools, load models, and validate API keys before the
        first real user request arrives.
        """
        self.initialize()
        logger.info("Pre-warming %d AI providers...", len(self._providers))
        for name, provider in self._providers.items():
            if name == "none":
                continue
            if hasattr(provider, "warmup"):
                await provider.warmup()
            else:
                # Fallback: run health check
                await provider.health_check()
        logger.info("AI provider warmup complete")
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

    async def health_check_all(self) -> dict[str, "ProviderHealthStatus"]:
        """Check health of all registered providers."""
        from ai_service.providers.litellm_provider import ProviderHealthStatus
        result: dict[str, ProviderHealthStatus] = {}
        for name, provider in self._providers.items():
            try:
                status = await provider.health_check()
                result[name] = status
            except Exception:
                result[name] = ProviderHealthStatus(
                    is_healthy=False,
                    provider_name=name,
                    error="Health check failed",
                )
        return result

    def get_available_api_models(self, tier: Optional[str] = None) -> List[str]:
        """Get available API model names, optionally filtered by tier."""
        return list_available_api_models(self.settings, tier=tier)

    def get_models_by_tier(self) -> dict:
        """Get models grouped by tier for frontend model selector."""
        return list_models_by_tier(self.settings)

    def _build_model_provider(
        self,
        model_name: str,
        tier: Optional[str] = None,
    ) -> Optional[BaseProvider]:
        """Build a single-model provider for a user-selected model.

        Returns a LiteLLMProvider pointing to exactly the requested model
        with no fallback chain. If litellm is not installed or the model
        is not found, returns None.
        """
        try:
            from ai_service.providers.litellm_provider import LiteLLMProvider
        except ImportError:
            logger.warning("litellm not installed; cannot build model provider")
            return None

        prefixed = f"openai/{model_name}" if not model_name.startswith("openai/") else model_name
        for p in self.settings.providers:
            if p.name == "api":
                model_match = p.model == prefixed or p.model.replace("openai/", "") == model_name
                if model_match:
                    if tier and p.tier != tier:
                        continue
                    api_key = get_api_key(p.env_key)
                    if not api_key:
                        continue
                    logger.info(
                        "Building single-model provider for %s (tier=%s)",
                        model_name, p.tier,
                    )
                    return LiteLLMProvider(
                        provider_name=f"api-{model_name}",
                        model_name=p.model,
                        base_url=p.base_url,
                        api_key=api_key,
                        is_local=False,
                        priority=10,
                        fallback_models=[],
                    )
        logger.warning("Model %s not found in provider config", model_name)
        return None

    def _build_tier_provider(
        self,
        tier: str,
    ) -> Optional[BaseProvider]:
        """Build a LiteLLMProvider filtered to only models of the given tier.

        This allows ``selected_tier="standard"`` to only use standard-tier models
        instead of all 19 models across all tiers. When tier-based filtering
        fails entirely, the catch-all ``api`` provider is used as fallback.
        """
        try:
            from ai_service.providers.litellm_provider import LiteLLMProvider
        except ImportError:
            return None

        tier_rows = [r for r in self._api_config_rows if r.tier == tier]
        if not tier_rows:
            logger.warning("No models found for tier %s", tier)
            return None

        primary = tier_rows[0]
        api_key = get_api_key(primary.env_key)
        if not api_key:
            return None

        fallback_models = []
        for fb_row in tier_rows[1:]:
            fb_key = get_api_key(fb_row.env_key)
            if fb_key:
                fallback_models.append(fb_row.model)

        logger.info(
            "Building tier-filtered provider: %s (%d models: %s + %d fallbacks)",
            tier, len(tier_rows), primary.model, len(fallback_models),
        )
        return LiteLLMProvider(
            provider_name=f"api-{tier}",
            model_name=primary.model,
            base_url=primary.base_url,
            api_key=api_key,
            is_local=False,
            priority=primary.priority,
            fallback_models=fallback_models,
            tier=tier,
        )


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
