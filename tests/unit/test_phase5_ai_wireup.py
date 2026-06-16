"""Tests for B13 AI metrics wire-up into the actual service modules.

These tests verify that when the AI service modules run their
real code paths, they emit the expected Prometheus metrics via
``backend.services.ai.metrics``.

Three integration points are tested:
  1. ``ai_service.safety.output_guard.guard_output`` emits
     ``ai_output_guard_flags_total`` and ``ai_output_guard_latency_seconds``.
  2. ``ai_service.rag.knowledge_service.compute_embedding`` emits
     ``ai_embedding_requests_total`` and ``ai_embedding_duration_seconds``.
  3. ``ai_service.providers.router.ProviderRouter.route_completion``
     emits ``ai_provider_requests_total`` and ``ai_provider_mode_active``.

The tests run each scenario in a *fresh* Python subprocess so the
Prometheus global REGISTRY starts empty. This avoids the
``Duplicated timeseries in CollectorRegistry`` error that arises
when multiple test files import the same metrics module under
different module names.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


# Helpers that are also defined inside the subprocess; redefined here
# only for documentation. The actual code uses the in-subprocess copy.
def _read_counter(reg, metric_name, label_filter):
    total = 0.0
    for m in reg.collect():
        if m.name != metric_name:
            continue
        for s in m.samples:
            if s.name.endswith("_created"):
                continue
            if label_filter:
                if not all(s.labels.get(k) == v for k, v in label_filter.items()):
                    continue
            total += float(s.value)
    return total


def _read_histogram_count(reg, metric_name):
    count = 0.0
    for m in reg.collect():
        if m.name != metric_name:
            continue
        for s in m.samples:
            if s.name.endswith("_count"):
                count += float(s.value)
    return count


_BODY = textwrap.dedent(
    """
    import json as _json
    import os as _os
    import sys as _sys
    _os.environ.setdefault('INFLUX_TOKEN', 'fake')
    _os.environ.setdefault('INFLUX_URL', 'http://localhost:8086')
    _os.environ.setdefault('INFLUX_ORG', 'test')
    _os.environ.setdefault('INFLUX_BUCKET', 'test')
    _os.environ.setdefault('DATABASE_URL', 'postgresql://test/test')
    _os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
    _os.environ.setdefault('JWT_SECRET', 'test')
    _sys.path.insert(0, r'__REPO__')

    def _read_counter(reg, metric_name, label_filter):
        total = 0.0
        for m in reg.collect():
            if m.name != metric_name:
                continue
            for s in m.samples:
                if s.name.endswith('_created'):
                    continue
                if label_filter:
                    if not all(s.labels.get(k) == v for k, v in label_filter.items()):
                        continue
                total += float(s.value)
        return total

    def _read_histogram_count(reg, metric_name):
        count = 0.0
        for m in reg.collect():
            if m.name != metric_name:
                continue
            for s in m.samples:
                if s.name.endswith('_count'):
                    count += float(s.value)
        return count

    __USER_SCRIPT__

    _sys.stdout.write('__RESULT__=' + _json.dumps(result) + '\\n')
    _sys.stdout.flush()
    """
)


def _run(result_bindings: str) -> dict:
    """Run a user script in a fresh subprocess.

    The script must end by assigning a ``result`` dict to local scope.
    The dict's values must be JSON-serializable scalars.
    """
    body = _BODY.replace("__REPO__", str(REPO))
    user = textwrap.dedent(result_bindings).rstrip()
    full = body.replace("__USER_SCRIPT__", user)
    out = subprocess.run(
        [sys.executable, "-c", full],
        capture_output=True, text=True, timeout=30,
    )
    result_line = None
    for line in out.stdout.splitlines():
        if line.startswith("__RESULT__="):
            result_line = line
            break
    assert result_line is not None, (
        f"child did not print __RESULT__ marker.\nstdout:\n{out.stdout}\n"
        f"stderr:\n{out.stderr}"
    )
    return json.loads(result_line[len("__RESULT__="):])


# ─────────────────────────────────────────────────────────────────────────────
# Output guard
# ─────────────────────────────────────────────────────────────────────────────


class TestOutputGuardMetrics:
    def test_unsafe_phrase_emits_unsafe_financial_flag(self):
        result = _run(
            """
            from prometheus_client import REGISTRY
            from ai_service.safety.output_guard import guard_output
            guard_output("I am 100% certain to call this a guaranteed winner.")
            v = _read_counter(REGISTRY, "ai_output_guard_flags",
                              {"flag_type": "unsafe_financial_claim"})
            result = {"flag_value": v}
            """
        )
        assert result["flag_value"] >= 1.0

    def test_code_pattern_emits_code_execution_flag(self):
        result = _run(
            """
            from prometheus_client import REGISTRY
            from ai_service.safety.output_guard import guard_output
            guard_output("Run this:\\n```python\\nimport os\\n```\\n")
            v = _read_counter(REGISTRY, "ai_output_guard_flags",
                              {"flag_type": "code_execution"})
            result = {"flag_value": v}
            """
        )
        assert result["flag_value"] >= 1.0

    def test_output_guard_observes_latency(self):
        result = _run(
            """
            from prometheus_client import REGISTRY
            from ai_service.safety.output_guard import guard_output
            guard_output("Safe response with disclaimer text.")
            c = _read_histogram_count(REGISTRY, "ai_output_guard_latency_seconds")
            result = {"hist_count": c}
            """
        )
        assert result["hist_count"] >= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Embedding
# ─────────────────────────────────────────────────────────────────────────────


class TestEmbeddingMetrics:
    def test_compute_embedding_records_request_when_unavailable(self):
        result = _run(
            """
            from prometheus_client import REGISTRY
            from ai_service.rag import knowledge_service as ks
            ks._get_embedding_model = lambda: None
            ks.compute_embedding("hello world")
            v = _read_counter(REGISTRY, "ai_embedding_requests",
                              {"model": "unavailable", "result": "error"})
            result = {"fail_value": v}
            """
        )
        assert result["fail_value"] >= 1.0

    def test_compute_embedding_records_success(self):
        result = _run(
            """
            import numpy as np
            from prometheus_client import REGISTRY
            from ai_service.rag import knowledge_service as ks

            class _FakeModel:
                def encode(self, text, normalize_embeddings=True):
                    return np.array([0.1, 0.2, 0.3, 0.4], dtype="float32")

            ks._get_embedding_model = lambda: _FakeModel()
            out = ks.compute_embedding("hello world")
            # ``record_embedding`` labels by model name and result
            # (``success`` or ``error``); we don't know the exact model
            # name in this test so we just count any ai_embedding_requests
            # sample with ``result=success``.
            v = _read_counter(REGISTRY, "ai_embedding_requests",
                              {"result": "success"})
            result = {"ok_value": v, "embedding_dim": len(out) if out else 0}
            """
        )
        assert result["ok_value"] >= 1.0
        assert result["embedding_dim"] == 4

    def test_compute_embedding_records_duration(self):
        result = _run(
            """
            import numpy as np
            from prometheus_client import REGISTRY
            from ai_service.rag import knowledge_service as ks

            class _FakeModel:
                def encode(self, text, normalize_embeddings=True):
                    return np.array([0.1, 0.2, 0.3], dtype="float32")

            ks._get_embedding_model = lambda: _FakeModel()
            ks.compute_embedding("hi")
            c = _read_histogram_count(REGISTRY, "ai_embedding_duration_seconds")
            result = {"hist_count": c}
            """
        )
        assert result["hist_count"] >= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Provider router
# ─────────────────────────────────────────────────────────────────────────────


class TestProviderRouterMetrics:
    def test_record_provider_mode_active_sets_gauge(self):
        result = _run(
            """
            from prometheus_client import REGISTRY
            from backend.services.ai import metrics as ai_metrics
            ai_metrics.record_provider_mode_active("auto")
            v = _read_counter(
                REGISTRY, "ai_provider_mode_active",
                {"provider": "local", "mode": "auto"},
            )
            result = {"mode_value": v}
            """
        )
        assert result["mode_value"] == 1.0

    def test_route_completion_emits_provider_request(self):
        """Successful routing to local provider should tick
        ``ai_provider_requests{provider=local,status=success}``."""
        result = _run(
            """
            import asyncio
            import dataclasses
            from prometheus_client import REGISTRY
            from backend.models.ai.providers import (
                LLMCompletionRequest, LLMCompletionResponse, ProviderInfo,
            )
            from ai_service.providers.router import ProviderRouter

            class _FakeProvider:
                def __init__(self, name):
                    self.name = name
                async def generate_chat_completion(self, request):
                    return LLMCompletionResponse(
                        content="hello",
                        model_name="fake-model",
                        provider=self.name,
                        is_mock=True,
                    )
                def get_info(self):
                    return ProviderInfo(
                        provider_name=self.name,
                        is_local=(self.name == "local"),
                        model_name="fake-model",
                    )

            async def main():
                router = ProviderRouter()
                router._providers = {
                    "local": _FakeProvider("local"),
                    "none": _FakeProvider("none"),
                }
                router._initialized = True
                router.settings = dataclasses.replace(router.settings, mode="local")
                req = LLMCompletionRequest(
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=64,
                )
                await router.route_completion(req)

            asyncio.run(main())
            v = _read_counter(REGISTRY, "ai_provider_requests",
                              {"provider": "local", "status": "success"})
            result = {"ok_value": v}
            """
        )
        assert result["ok_value"] >= 1.0

    def test_route_completion_records_failure_then_fallback(self):
        result = _run(
            """
            import asyncio
            import dataclasses
            from prometheus_client import REGISTRY
            from backend.models.ai.providers import (
                LLMCompletionRequest, LLMCompletionResponse, ProviderInfo,
            )
            from ai_service.providers.router import ProviderRouter

            class _Boom:
                def __init__(self, name):
                    self.name = name
                async def generate_chat_completion(self, request):
                    raise RuntimeError("simulated outage")
                def get_info(self):
                    return ProviderInfo(provider_name=self.name, is_local=True, model_name="x")

            class _None:
                async def generate_chat_completion(self, request):
                    return LLMCompletionResponse(
                        content="fallback", model_name="none-model",
                        provider="none", is_mock=True,
                    )
                def get_info(self):
                    return ProviderInfo(provider_name="none", is_local=True, model_name="none-model")

            async def main():
                router = ProviderRouter()
                router._providers = {"local": _Boom("local"), "none": _None()}
                router._initialized = True
                router.settings = dataclasses.replace(router.settings, mode="local")
                req = LLMCompletionRequest(
                    messages=[{"role": "user", "content": "hi"}], max_tokens=64,
                )
                await router.route_completion(req)

            asyncio.run(main())
            v_failure = _read_counter(REGISTRY, "ai_provider_requests",
                                      {"provider": "local", "status": "failure"})
            v_chain = _read_histogram_count(REGISTRY, "ai_provider_chain_depth")
            result = {"fail_value": v_failure, "chain_count": v_chain}
            """
        )
        assert result["fail_value"] >= 1.0
        assert result["chain_count"] >= 1.0
