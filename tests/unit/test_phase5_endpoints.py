"""Tests for the custom Prometheus endpoints declared in ``prometheus.yml``.

Three jobs in ``config/prometheus.yml`` point at FastAPI on non-default paths:
    - /metrics         (default prometheus-fastapi-instrumentator)
    - /metrics-custom  (backend/api/metrics.py: HTTP, WS, multi-source, cache, Trino)
    - /metrics-ai      (backend/services/ai/metrics.py: AI, RAG, scope gate, cost)

These tests use the FastAPI TestClient to bring the app up in-process and
assert the endpoints respond with valid Prometheus exposition format and
contain the expected metric families (via ``# HELP`` headers, which appear
even for zero-valued metrics).
"""

from __future__ import annotations

import os

# Set required env vars BEFORE importing the app (Pydantic-settings validation)
os.environ.setdefault("INFLUX_TOKEN", "fake-token")
os.environ.setdefault("INFLUX_URL", "http://localhost:8086")
os.environ.setdefault("INFLUX_ORG", "test")
os.environ.setdefault("INFLUX_BUCKET", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-for-import-only")

import pytest
import sys
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Spin up the FastAPI app once for the whole module.

    Other test files (``test_phase5_flink_metrics_pure.py`` in
    particular) deliberately clear the global Prometheus
    ``REGISTRY`` as part of their setup. We defensively reload
    every metrics module + the FastAPI app *after* any such
    teardown so the custom endpoints always see the freshly
    re-registered collectors.

    Important: the metrics modules must be re-registered under
    their canonical dotted names (``backend.api.metrics``,
    ``backend.services.ai.metrics``) so that
    ``from backend.api.metrics import record_ws_connection`` in
    test code resolves to the SAME module instance the FastAPI
    app is using. Loading under an alias like
    ``spec_from_file_location('backend_api_metrics', ...)``
    would create a second module instance, and helper calls
    would mutate a *different* REGISTRY collector than the one
    the endpoint exposes.
    """
    import importlib
    from pathlib import Path
    from prometheus_client import REGISTRY

    # 1. Make sure the registry is clean (in case a previous
    #    test module wiped it).
    for c in list(REGISTRY._names_to_collectors.values()):
        try:
            REGISTRY.unregister(c)
        except Exception:
            pass

    # 2. Drop any cached module references so the re-imports
    #    below create fresh instances bound to the clean registry.
    for dotted in [
        "backend.app",
        "backend.api.metrics",
        "backend.services.ai.metrics",
        "src.producer.metrics",
        "src.processing.writers.metrics",
    ]:
        sys.modules.pop(dotted, None)

    # 3. Re-load the four metrics modules under their canonical
    #    dotted names. We use ``importlib.import_module`` so the
    #    module registry (sys.modules) carries the standard names.
    repo = Path(__file__).resolve().parent.parent.parent
    for dotted, relpath in [
        ("backend.api.metrics", "backend/api/metrics.py"),
        ("backend.services.ai.metrics", "backend/services/ai/metrics.py"),
        ("src.producer.metrics", "src/producer/metrics.py"),
        ("src.processing.writers.metrics", "src/processing/writers/metrics.py"),
    ]:
        path = str(repo / relpath)
        spec = importlib.util.spec_from_file_location(dotted, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = mod
        spec.loader.exec_module(mod)

    # 4. Now import the FastAPI app — it'll see the freshly
    #    registered metrics and its _CUSTOM_METRIC_NAMES /
    #    _AI_METRIC_NAMES sets will be derived from the same
    #    module objects that test code imports.
    from backend.app import app  # noqa: WPS433
    return TestClient(app)


def _help_names(text: str) -> set[str]:
    """Extract the bare metric name from every ``# HELP <name> ...`` line.

    This works for zero-valued metrics because prometheus_client always
    emits a HELP+TYPE header for every declared metric, even before any
    ``.inc()`` / ``.set()`` call. Sample-value lines (``<name> 0``) are
    only emitted once a metric has been observed at least once.
    """
    names: set[str] = set()
    for ln in text.splitlines():
        if ln.startswith("# HELP "):
            # Format: # HELP <name> <doc>
            rest = ln[len("# HELP "):]
            name = rest.split(" ", 1)[0]
            names.add(name)
    return names


# ─────────────────────────────────────────────────────────────────────────────
# /metrics — default prometheus-fastapi-instrumentator
# ─────────────────────────────────────────────────────────────────────────────


class TestMetricsDefaultEndpoint:
    def test_default_metrics_endpoint_returns_200(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_default_metrics_exposition_format(self, client):
        r = client.get("/metrics")
        assert r.text.startswith("# HELP") or r.text.startswith("# TYPE")

    def test_default_metrics_content_type(self, client):
        r = client.get("/metrics")
        ct = r.headers.get("content-type", "")
        assert "text/plain" in ct
        assert "version=" in ct


# ─────────────────────────────────────────────────────────────────────────────
# /metrics-custom — backend/api/metrics.py
# ─────────────────────────────────────────────────────────────────────────────


class TestMetricsCustomEndpoint:
    def test_custom_endpoint_returns_200(self, client):
        r = client.get("/metrics-custom")
        assert r.status_code == 200

    def test_custom_endpoint_returns_valid_prometheus_format(self, client):
        r = client.get("/metrics-custom")
        assert "# HELP " in r.text
        assert "# TYPE " in r.text

    def test_custom_endpoint_contains_websocket_metrics(self, client):
        """Note: prometheus_client emits ``# HELP`` with the base name
        (no ``_total`` suffix for counters) but the sample line gets the
        suffix. We assert on the HELP name."""
        r = client.get("/metrics-custom")
        names = _help_names(r.text)
        assert "websocket_connections_active" in names
        assert "websocket_connection_attempts" in names
        assert "websocket_message_push_duration_seconds" in names
        assert "websocket_message_size_bytes" in names

    def test_custom_endpoint_contains_multi_source_metrics(self, client):
        r = client.get("/metrics-custom")
        names = _help_names(r.text)
        assert "multi_source_lookups" in names
        assert "source_lookup_duration_seconds" in names
        assert "source_unavailable" in names
        assert "source_stale_data" in names

    def test_custom_endpoint_contains_cache_metrics(self, client):
        r = client.get("/metrics-custom")
        names = _help_names(r.text)
        assert "api_cache_ops" in names
        assert "api_cache_entry_age_seconds" in names
        assert "api_cache_size_entries" in names

    def test_custom_endpoint_contains_trino_metrics(self, client):
        """B11 — Trino observability metrics are declared."""
        r = client.get("/metrics-custom")
        names = _help_names(r.text)
        assert "backend_trino_query_duration_seconds" in names
        assert "backend_trino_query_failures" in names
        assert "backend_trino_active_queries" in names
        assert "backend_trino_fallback" in names

    def test_custom_endpoint_emits_after_helper_call(self, client):
        """Sanity: the endpoint reflects real-time metric state.

        The fixture below pre-loads the metrics modules under the
        SAME module name (``backend.api.metrics``) that ``app.py``
        uses, so any helper we call here mutates the same counters
        the /metrics-custom endpoint exposes.
        """
        from backend.api.metrics import record_ws_connection

        def _total(text: str, base: str) -> float:
            total = 0.0
            for ln in text.splitlines():
                if ln.startswith(f"{base}_total{{") and 'result="accepted"' in ln:
                    try:
                        total += float(ln.rsplit(" ", 1)[1])
                    except ValueError:
                        pass
            return total

        before = _total(client.get("/metrics-custom").text, "websocket_connection_attempts")
        record_ws_connection(route="/stream/test_endpoint", accepted=True)
        after = _total(client.get("/metrics-custom").text, "websocket_connection_attempts")
        assert after > before, f"expected counter to tick: before={before}, after={after}"


# ─────────────────────────────────────────────────────────────────────────────
# /metrics-ai — backend/services/ai/metrics.py
# ─────────────────────────────────────────────────────────────────────────────


class TestMetricsAIEndpoint:
    def test_ai_endpoint_returns_200(self, client):
        r = client.get("/metrics-ai")
        assert r.status_code == 200

    def test_ai_endpoint_contains_scope_gate_metrics(self, client):
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        assert "ai_scope_gate_decisions" in names
        assert "ai_scope_gate_latency_seconds" in names

    def test_ai_endpoint_contains_provider_metrics(self, client):
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        assert "ai_provider_requests" in names
        assert "ai_provider_latency_seconds" in names
        assert "ai_provider_chain_depth" in names

    def test_ai_endpoint_contains_rag_metrics(self, client):
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        assert "ai_rag_retrieval_duration_seconds" in names
        assert "ai_rag_zero_results" in names
        assert "ai_rag_relevance_score" in names
        assert "ai_rag_cache_ops" in names
        assert "ai_rag_vector_search_duration_seconds" in names
        assert "ai_rag_filter_outcomes" in names

    def test_ai_endpoint_contains_output_guard_metrics(self, client):
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        assert "ai_output_guard_flags" in names
        assert "ai_output_guard_latency_seconds" in names
        assert "ai_output_guard_severity" in names

    def test_ai_endpoint_contains_cost_metrics(self, client):
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        assert "ai_cost_usd" in names
        assert "ai_tokens_used" in names
        assert "ai_tokens_per_request" in names

    def test_ai_endpoint_contains_chat_metrics(self, client):
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        assert "ai_chat_sessions_created" in names
        assert "ai_active_sessions" in names
        assert "ai_messages_stored" in names

    def test_ai_endpoint_contains_rag_dashboard_aliases(self, client):
        """The rag-knowledge-base dashboard references 8 alias metrics.
        All of them must be declared so Prometheus queries resolve.

        Note: prometheus_client's ``# HELP`` header uses the base metric
        name (no ``_total`` suffix for counters); sample lines get the
        ``_total`` suffix when the counter has been incremented.
        """
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        expected = {
            "ai_knowledge_base_chunk_count",
            "ai_knowledge_base_size_bytes",
            "ai_knowledge_base_last_ingest_timestamp",
            "ai_knowledge_base_oldest_chunk_timestamp",
            "ai_embedding_dimensions",
            "ai_knowledge_base_source",
            "ai_rag_retrieval",
            "ai_retrieval_log",
        }
        for m in expected:
            assert m in names, f"Missing HELP for {m}"

    def test_ai_endpoint_emits_after_helper_call(self, client):
        """Sanity: AI endpoint reflects real-time metric state."""
        from backend.services.ai.metrics import (
            record_ai_request_start,
            record_ai_request_finish,
        )

        def _count(text: str, base: str) -> float:
            for ln in text.splitlines():
                if ln.startswith(f"{base}_total{{") and 'status="success"' in ln:
                    try:
                        return float(ln.rsplit(" ", 1)[1])
                    except ValueError:
                        return 0.0
            return 0.0

        before = _count(client.get("/metrics-ai").text, "ai_requests")
        record_ai_request_start()
        record_ai_request_finish(status="success", duration_sec=0.1)
        after = _count(client.get("/metrics-ai").text, "ai_requests")
        assert after > before, f"expected counter to tick: before={before}, after={after}"


# ─────────────────────────────────────────────────────────────────────────────
# Cross-endpoint isolation
# ─────────────────────────────────────────────────────────────────────────────


class TestEndpointIsolation:
    def test_custom_endpoint_does_not_leak_ai_metrics(self, client):
        r = client.get("/metrics-custom")
        names = _help_names(r.text)
        assert "ai_scope_gate_decisions" not in names
        assert "ai_cost_usd" not in names
        assert "ai_rag_retrieval_duration_seconds" not in names

    def test_ai_endpoint_does_not_leak_websocket_metrics(self, client):
        r = client.get("/metrics-ai")
        names = _help_names(r.text)
        assert "websocket_connections_active" not in names
        assert "multi_source_lookups" not in names
        assert "api_cache_ops" not in names
        assert "backend_trino_query_duration_seconds" not in names

    def test_custom_endpoint_carries_app_level_metrics(self, client):
        """The /metrics-custom endpoint is the place where
        multi-source, WebSocket, cache, and Trino metrics live."""
        custom_names = _help_names(client.get("/metrics-custom").text)
        # These are the families that ``prometheus.yml`` expects
        # from the fastapi:8000/metrics-custom job
        overlap_expected = {
            "multi_source_lookups",
            "websocket_connections_active",
            "backend_trino_query_duration_seconds",
            "api_cache_ops",
        }
        assert overlap_expected <= custom_names, (
            f"Custom endpoint missing {overlap_expected - custom_names}"
        )
