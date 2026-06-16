"""Tests for provider health monitoring and circuit breaker."""
from __future__ import annotations

import pytest
from ai_service.providers.health import (
    CircuitBreaker,
    CircuitState,
    ProviderHealth,
    ProviderHealthMonitor,
    get_health_monitor,
)


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.should_allow() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.should_allow() is False

    def test_success_resets(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failures == 0

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=0)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # With 0 timeout, should immediately transition to half-open
        assert cb.should_allow() is True
        assert cb.state == CircuitState.HALF_OPEN


class TestProviderHealthMonitor:
    def test_register_provider(self):
        monitor = ProviderHealthMonitor()
        monitor.register("vllm")
        assert monitor.should_try("vllm") is True

    def test_unregistered_always_allowed(self):
        monitor = ProviderHealthMonitor()
        assert monitor.should_try("unknown_provider") is True

    def test_record_success(self):
        monitor = ProviderHealthMonitor()
        monitor.register("vllm")
        monitor.record_success("vllm", latency_ms=150)
        health = monitor.get_health("vllm")
        assert health.is_healthy is True
        assert health.last_latency_ms == 150

    def test_record_failure_opens_circuit(self):
        monitor = ProviderHealthMonitor()
        monitor.register("vllm", failure_threshold=2)
        monitor.record_failure("vllm")
        monitor.record_failure("vllm")
        assert monitor.should_try("vllm") is False

    def test_get_all_health(self):
        monitor = ProviderHealthMonitor()
        monitor.register("vllm")
        monitor.register("litellm")
        monitor.record_success("vllm", latency_ms=100)
        all_health = monitor.get_all_health()
        assert "vllm" in all_health
        assert "litellm" in all_health
        assert all_health["vllm"]["is_healthy"] is True

    def test_get_best_provider(self):
        monitor = ProviderHealthMonitor()
        monitor.register("vllm")
        monitor.register("litellm")
        monitor.record_success("vllm", latency_ms=50)
        monitor.record_success("litellm", latency_ms=200)
        best = monitor.get_best_provider(["vllm", "litellm"])
        assert best == "vllm"

    def test_best_provider_skips_open_circuit(self):
        monitor = ProviderHealthMonitor()
        monitor.register("vllm", failure_threshold=1)
        monitor.register("litellm")
        monitor.record_failure("vllm")
        monitor.record_success("litellm", latency_ms=200)
        best = monitor.get_best_provider(["vllm", "litellm"])
        assert best == "litellm"

    def test_success_rate(self):
        health = ProviderHealth(provider_name="test")
        assert health.success_rate == 0.0
        health.total_requests = 10
        health.total_failures = 3
        assert health.success_rate == 0.7
