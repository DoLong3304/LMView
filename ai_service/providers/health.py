"""Provider health monitoring with circuit breaker pattern.

Monitors LLM provider health (vLLM, LiteLLM, API) and implements
circuit breaker logic to avoid cascading failures.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger("ai_service.providers.health")

# Circuit breaker defaults
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_RECOVERY_TIMEOUT_S = 60
DEFAULT_HEALTH_CHECK_INTERVAL_S = 15


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing — skip provider
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class ProviderHealth:
    """Health state for a single provider."""
    provider_name: str
    is_healthy: bool = False
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    last_check_time: Optional[float] = None
    last_latency_ms: Optional[int] = None
    total_requests: int = 0
    total_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.total_requests - self.total_failures) / self.total_requests


@dataclass
class CircuitBreaker:
    """Circuit breaker for a provider."""
    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD
    recovery_timeout_s: float = DEFAULT_RECOVERY_TIMEOUT_S
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    last_failure_time: float = 0.0

    def record_success(self) -> None:
        """Record successful request — close circuit."""
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record failed request — possibly open circuit."""
        self.failures += 1
        self.last_failure_time = time.monotonic()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPENED after %d failures.", self.failures,
            )

    def should_allow(self) -> bool:
        """Check if the circuit allows a request."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.recovery_timeout_s:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state.")
                return True
            return False
        # HALF_OPEN: allow one test request
        return True


class ProviderHealthMonitor:
    """Monitor health of LLM providers with circuit breakers.

    Usage::

        monitor = ProviderHealthMonitor()
        if monitor.should_try("vllm"):
            try:
                result = await provider.call(...)
                monitor.record_success("vllm", latency_ms=150)
            except Exception:
                monitor.record_failure("vllm")
    """

    def __init__(self):
        self._health: Dict[str, ProviderHealth] = {}
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._check_task: Optional[asyncio.Task] = None

    def register(
        self,
        provider_name: str,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout_s: float = DEFAULT_RECOVERY_TIMEOUT_S,
    ) -> None:
        """Register a provider for health monitoring."""
        self._health[provider_name] = ProviderHealth(provider_name=provider_name)
        self._circuits[provider_name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout_s=recovery_timeout_s,
        )
        logger.info("Registered provider '%s' for health monitoring.", provider_name)

    def should_try(self, provider_name: str) -> bool:
        """Check if provider should be attempted (circuit allows it)."""
        circuit = self._circuits.get(provider_name)
        if not circuit:
            return True  # Unregistered providers always allowed
        return circuit.should_allow()

    def record_success(self, provider_name: str, latency_ms: int = 0) -> None:
        """Record a successful provider call."""
        health = self._health.get(provider_name)
        circuit = self._circuits.get(provider_name)
        now = time.monotonic()

        if health:
            health.is_healthy = True
            health.consecutive_failures = 0
            health.last_success_time = now
            health.last_check_time = now
            health.last_latency_ms = latency_ms
            health.total_requests += 1

        if circuit:
            circuit.record_success()

    def record_failure(self, provider_name: str) -> None:
        """Record a failed provider call."""
        health = self._health.get(provider_name)
        circuit = self._circuits.get(provider_name)
        now = time.monotonic()

        if health:
            health.is_healthy = False
            health.consecutive_failures += 1
            health.last_failure_time = now
            health.last_check_time = now
            health.total_requests += 1
            health.total_failures += 1

        if circuit:
            circuit.record_failure()

    def get_health(self, provider_name: str) -> Optional[ProviderHealth]:
        """Get health state for a provider."""
        return self._health.get(provider_name)

    def get_all_health(self) -> Dict[str, Dict]:
        """Get health summary for all providers."""
        return {
            name: {
                "is_healthy": h.is_healthy,
                "circuit_state": h.circuit_state.value,
                "consecutive_failures": h.consecutive_failures,
                "success_rate": round(h.success_rate, 3),
                "last_latency_ms": h.last_latency_ms,
                "total_requests": h.total_requests,
            }
            for name, h in self._health.items()
        }

    def get_best_provider(self, candidates: list[str]) -> Optional[str]:
        """Select the best healthy provider from candidates.

        Prefers:
        1. Healthy providers with open circuits
        2. Lower latency
        3. Higher success rate
        """
        available = []
        for name in candidates:
            if self.should_try(name):
                health = self._health.get(name)
                if health:
                    available.append((name, health))
                else:
                    available.append((name, ProviderHealth(provider_name=name)))

        if not available:
            return None

        # Sort by: healthy first, then by latency, then success rate
        def sort_key(item):
            name, h = item
            return (
                not h.is_healthy,
                h.last_latency_ms or 99999,
                -h.success_rate,
            )

        available.sort(key=sort_key)
        return available[0][0]


# Module-level singleton
_monitor: Optional[ProviderHealthMonitor] = None


def get_health_monitor() -> ProviderHealthMonitor:
    """Get or create the singleton health monitor."""
    global _monitor
    if _monitor is None:
        _monitor = ProviderHealthMonitor()
    return _monitor
