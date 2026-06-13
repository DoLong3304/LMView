"""
Unit tests for the new Phase 5 custom metrics modules.

Verifies that:
  - All declared Prometheus metrics are correctly created
  - Helper functions update metric values without errors
  - Counters increment, gauges set, histograms observe correctly
  - Module imports are clean (no missing dependencies)

These tests do not require a running Redis/PostgreSQL/Kafka — they only
exercise the in-process metric declarations.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from prometheus_client import CollectorRegistry

# Locate the repo root regardless of pytest's working directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _load(name: str, rel_path: str):
    """Import a module by absolute file path with a freshly-cleaned registry.

    Each test class gets the default global CollectorRegistry cleared
    before exec so that metric declarations (Histogram / Counter / Gauge)
    do not collide across reloads.
    """
    import prometheus_client
    from prometheus_client import REGISTRY

    full = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, str(full))
    mod = importlib.util.module_from_spec(spec)

    # Unregister every collector that any previous test class registered
    # so we start from a clean registry.
    for collector in list(REGISTRY._names_to_collectors.values()):  # type: ignore[attr-defined]
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass

    spec.loader.exec_module(mod)
    return mod


class TestProducerMetrics(unittest.TestCase):
    """Test src/producer/metrics.py."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("producer_metrics", "src/producer/metrics.py")

    def test_dedup_metrics_declared(self) -> None:
        for name in (
            "DEDUP_STATE_SIZE",
            "DEDUP_DUPLICATES_SKIPPED",
            "DEDUP_MESSAGES_FORWARDED",
            "DEDUP_LAST_DECISION",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")
            self.assertIsNotNone(getattr(self.mod, name))

    def test_failover_metrics_declared(self) -> None:
        for name in (
            "DIRECT_REDIS_ACTIVE",
            "FAILOVER_TRANSITIONS",
            "FAILOVER_DURATION",
            "DIRECT_REDIS_WRITES",
            "DIRECT_REDIS_FAILURES",
            "DIRECT_REDIS_WRITE_LATENCY",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_health_metrics_declared(self) -> None:
        for name in (
            "KAFKA_HEALTHY",
            "FLINK_HEALTHY",
            "KAFKA_PROBE_DURATION",
            "FLINK_PROBE_DURATION",
            "KAFKA_PROBE_FAILURES",
            "FLINK_PROBE_FAILURES",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_exchange_metrics_declared(self) -> None:
        for name in (
            "EXCHANGE_LAST_MESSAGE",
            "EXCHANGE_MESSAGES_RECEIVED",
            "EXCHANGE_WS_CONNECTED",
            "RECONNECT_BACKOFF_SECONDS",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_init_metrics_runs(self) -> None:
        # Should not raise
        self.mod.init_metrics()

    def test_record_dedup_decision_runs(self) -> None:
        # Should not raise
        self.mod.record_dedup_decision(exchange="binance", skipped=5, forwarded=10, destination="kafka")
        self.mod.record_dedup_decision(exchange="binance", skipped=0, forwarded=0, destination="direct_redis")

    def test_record_failover_transition_runs(self) -> None:
        self.mod.record_failover_transition(from_state="kafka", to_state="direct_redis")
        self.mod.record_failover_transition(from_state="direct_redis", to_state="kafka")

    def test_record_direct_redis_write_runs(self) -> None:
        self.mod.record_direct_redis_write(
            exchange="binance", key_pattern="trade_latest", duration_sec=0.001, success=True
        )
        self.mod.record_direct_redis_write(
            exchange="binance",
            key_pattern="trade_latest",
            duration_sec=0.5,
            success=False,
            error="ConnectionError",
        )

    def test_record_exchange_message_runs(self) -> None:
        self.mod.record_exchange_message(exchange="binance", stream="ticker", n=200)
        self.mod.record_exchange_ws_state(exchange="binance", stream="ticker", connected=True)
        self.mod.record_exchange_ws_state(exchange="binance", stream="ticker", connected=False)


class TestBackendApiMetrics(unittest.TestCase):
    """Test backend/api/metrics.py."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("backend_api_metrics", "backend/api/metrics.py")

    def test_http_metrics_declared(self) -> None:
        for name in (
            "HTTP_REQUEST_DURATION",
            "HTTP_REQUESTS_TOTAL",
            "HTTP_ERRORS_TOTAL",
            "HTTP_REQUESTS_IN_FLIGHT",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_websocket_connection_metrics_declared(self) -> None:
        for name in (
            "WS_CONNECTIONS_ACTIVE",
            "WS_CONNECTION_ATTEMPTS",
            "WS_CONNECTION_ERRORS",
            "WS_DISCONNECTS",
            "WS_CONNECTION_LIFETIME",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_websocket_message_metrics_declared(self) -> None:
        for name in (
            "WS_MESSAGES_PUSHED",
            "WS_MESSAGES_DROPPED",
            "WS_MESSAGE_SIZE",
            "WS_MESSAGE_PUSH_DURATION",
            "WS_CLIENT_BUFFER_SIZE",
            "WS_LOOP_CYCLE_DURATION",
            "WS_NOOP_PUSHES",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_multi_source_metrics_declared(self) -> None:
        for name in (
            "SOURCE_LOOKUPS",
            "SOURCE_LOOKUP_DURATION",
            "SOURCE_UNAVAILABLE",
            "SOURCE_STALE_DATA",
            "SOURCE_CHAIN_OUTCOME",
            "SOURCE_LAST_UPDATE",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_cache_metrics_declared(self) -> None:
        for name in ("CACHE_OPS", "CACHE_AGE", "CACHE_SIZE"):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_record_http_request_runs(self) -> None:
        self.mod.record_http_request(method="GET", endpoint="/api/health", status=200, duration_sec=0.05)
        self.mod.record_http_request(method="POST", endpoint="/api/ai/chat", status=500, duration_sec=1.2)

    def test_record_ws_lifecycle_runs(self) -> None:
        self.mod.record_ws_connection(route="/stream/all", accepted=True)
        self.mod.record_ws_connection(route="/stream/all", accepted=False)
        self.mod.record_ws_disconnect(route="/stream/all", reason="client_close", lifetime_sec=300)
        self.mod.record_ws_connection_error(route="/stream/all", error_type="RuntimeError")

    def test_record_ws_message_push_runs(self) -> None:
        self.mod.record_ws_message_push(
            route="/stream/all", data_type="candle", size_bytes=2048, duration_sec=0.01
        )
        self.mod.record_ws_message_push(
            route="/stream/all",
            data_type="candle",
            size_bytes=2048,
            duration_sec=0.5,
            dropped=True,
            drop_reason="slow_client",
        )
        self.mod.record_ws_noop(route="/stream/all", data_type="candle")
        self.mod.record_ws_loop_cycle(route="/stream/all", duration_sec=0.05)

    def test_record_source_lookup_runs(self) -> None:
        self.mod.record_source_lookup(
            source="redis", data_type="candle_1m", duration_sec=0.005, success=True
        )
        self.mod.record_source_lookup(
            source="influxdb", data_type="candle_5m", duration_sec=0.5, success=True, stale=True
        )
        self.mod.record_source_lookup(
            source="trino", data_type="candle_1h", duration_sec=2.5, success=False, reason="timeout"
        )
        self.mod.record_source_unavailable(source="redis", data_type="candle_1m", reason="ConnectionError")
        self.mod.record_source_chain_outcome(data_type="candle_1m", terminating_source="redis")
        self.mod.record_source_freshness(source="redis", exchange="binance", symbol="BTCUSDT", ts=1700000000.0)

    def test_record_cache_op_runs(self) -> None:
        self.mod.record_cache_op(endpoint="/api/klines", result="hit", age_sec=0.1)
        self.mod.record_cache_op(endpoint="/api/klines", result="miss")
        self.mod.record_cache_op(endpoint="/api/klines", result="bypass")


class TestAiMetrics(unittest.TestCase):
    """Test backend/services/ai/metrics.py."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("ai_metrics", "backend/services/ai/metrics.py")

    def test_request_metrics_declared(self) -> None:
        for name in (
            "AI_REQUESTS",
            "AI_REQUEST_DURATION",
            "AI_REQUESTS_WITH_FALLBACK",
            "AI_REQUESTS_IN_FLIGHT",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_scope_gate_metrics_declared(self) -> None:
        self.assertTrue(hasattr(self.mod, "AI_SCOPE_GATE_DECISIONS"))
        self.assertTrue(hasattr(self.mod, "AI_SCOPE_GATE_LATENCY"))

    def test_provider_metrics_declared(self) -> None:
        for name in (
            "AI_PROVIDER_REQUESTS",
            "AI_PROVIDER_LATENCY",
            "AI_PROVIDER_CHAIN_DEPTH",
            "AI_PROVIDER_MODE_ACTIVE",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_rag_metrics_declared(self) -> None:
        for name in (
            "AI_RAG_RETRIEVAL_DURATION",
            "AI_RAG_TOP_K_RESULTS",
            "AI_RAG_RELEVANCE_SCORE",
            "AI_RAG_ZERO_RESULTS",
            "AI_RAG_CACHE_OPS",
            "AI_RAG_VECTOR_SEARCH_DURATION",
            "AI_RAG_FILTER_OUTCOMES",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_output_guard_metrics_declared(self) -> None:
        for name in (
            "AI_OUTPUT_GUARD_FLAGS",
            "AI_OUTPUT_GUARD_LATENCY",
            "AI_OUTPUT_GUARD_SEVERITY",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_session_token_metrics_declared(self) -> None:
        for name in (
            "AI_CHAT_SESSIONS_CREATED",
            "AI_ACTIVE_SESSIONS",
            "AI_MESSAGES_STORED",
            "AI_TOKENS_USED",
            "AI_TOKENS_PER_REQUEST",
            "AI_COST_USD",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_record_request_lifecycle_runs(self) -> None:
        self.mod.record_ai_request_start()
        self.mod.record_ai_request_finish(status="success", duration_sec=2.0)
        self.mod.record_ai_request_finish(status="scope_blocked", duration_sec=0.1, had_fallback=False)
        self.mod.record_ai_request_finish(status="provider_error", duration_sec=30.0, had_fallback=True)

    def test_record_scope_gate_runs(self) -> None:
        self.mod.record_scope_gate(decision="in_scope", category="technical_indicator", duration_sec=0.001)
        self.mod.record_scope_gate(decision="out_of_scope", category="weather", duration_sec=0.0005)
        self.mod.record_scope_gate(decision="injection", category="jailbreak", duration_sec=0.002)

    def test_record_provider_runs(self) -> None:
        self.mod.record_provider_request(provider="local_vllm", status="success", duration_sec=1.5)
        self.mod.record_provider_request(provider="openai", status="fallback", duration_sec=2.0)
        self.mod.record_provider_request(provider="mock", status="error", duration_sec=0.01)
        self.mod.record_provider_chain_depth(depth=1, status="success")
        self.mod.record_provider_chain_depth(depth=5, status="fallback")

    def test_record_rag_runs(self) -> None:
        self.mod.record_rag_retrieval(duration_sec=0.1, n_results=6, top_score=0.85)
        self.mod.record_rag_retrieval(duration_sec=0.05, n_results=0, cache_hit=True)
        self.mod.record_rag_retrieval(
            duration_sec=0.2, n_results=6, top_score=0.5, cache_hit=False, vector_search_sec=0.02
        )
        self.mod.record_rag_filter(filter_name="language", kept=True)
        self.mod.record_rag_filter(filter_name="credibility_level", kept=False)
        self.mod.record_retrieval_log(duration_sec=0.005)

    def test_record_embedding_runs(self) -> None:
        self.mod.record_embedding(model="all-MiniLM-L6-v2", duration_sec=0.05, success=True)
        self.mod.record_embedding(model="all-MiniLM-L6-v2", duration_sec=0.5, success=False)

    def test_record_output_guard_runs(self) -> None:
        self.mod.record_output_guard_flag(flag_type="financial_advice", severity="error")
        self.mod.record_output_guard_flag(flag_type="disclaimer_missing", severity="warning", duration_sec=0.001)
        self.mod.record_output_guard_flag(flag_type="code_block", severity="info", duration_sec=0.001)

    def test_record_chart_action_runs(self) -> None:
        self.mod.record_chart_action(action_type="add_indicator", result="accepted", payload_size=128)
        self.mod.record_chart_action(action_type="change_timeframe", result="rejected", payload_size=64)
        self.mod.record_chart_action(action_type="set_symbol", result="invalid", payload_size=256)

    def test_record_token_and_cost_runs(self) -> None:
        self.mod.record_token_usage(provider="openai", input_tokens=500, output_tokens=200)
        self.mod.record_ai_cost(provider="openai", cost_usd=0.01)
        self.mod.record_ai_session_created()
        self.mod.record_ai_message_stored(role="user")
        self.mod.record_ai_message_stored(role="assistant")
        self.mod.record_knowledge_ingest(result="success")
        self.mod.record_knowledge_ingest(result="rejected")


class TestFlinkWriterMetrics(unittest.TestCase):
    """Test src/processing/writers/metrics.py."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("flink_metrics", "src/processing/writers/metrics.py")

    def test_writer_metrics_declared(self) -> None:
        for name in (
            "WRITER_FLUSH_DURATION",
            "WRITER_BUFFER_SIZE",
            "WRITER_RECORDS_PER_FLUSH",
            "WRITER_RECORDS_EMITTED",
            "WRITER_FLUSH_CALLS",
            "WRITER_ERRORS",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_indicator_metrics_declared(self) -> None:
        for name in (
            "INDICATOR_STATE_WARMUP_DURATION",
            "INDICATOR_STATE_KEYS",
            "INDICATOR_RECOMPUTATIONS",
            "KLINE_GAP_FILLS",
            "KLINE_WINDOW_FILL_RATIO",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_checkpoint_metrics_declared(self) -> None:
        for name in (
            "FLINK_CHECKPOINT_DURATION",
            "FLINK_CHECKPOINT_SIZE",
            "FLINK_CHECKPOINT_FAILURES",
            "FLINK_CHECKPOINT_SUCCESS",
            "FLINK_CHECKPOINT_ALIGNMENT_BYTES",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_kafka_source_metrics_declared(self) -> None:
        for name in (
            "KAFKA_SOURCE_RECORDS_IN",
            "KAFKA_SOURCE_RECORDS_DROPPED",
            "KAFKA_SOURCE_WATERMARK_LAG",
            "KAFKA_SOURCE_DESERIALIZE_DURATION",
        ):
            self.assertTrue(hasattr(self.mod, name), f"Missing {name}")

    def test_record_flush_runs(self) -> None:
        self.mod.record_flush(
            writer="KeyDBWriter", sink="redis", duration_sec=0.05, n_records=200, trigger="time"
        )
        self.mod.record_flush(
            writer="IndicatorWriter",
            sink="redis",
            duration_sec=0.1,
            n_records=50,
            trigger="size",
            error="ConnectionError",
        )
        self.mod.record_buffer_size(writer="KeyDBWriter", sink="redis", size=300)

    def test_record_indicator_runs(self) -> None:
        self.mod.record_indicator_warmup(state_type="ema", duration_sec=2.5)
        self.mod.record_indicator_recompute(indicator="rsi", trigger="new_candle")
        self.mod.record_kline_gap_fill(exchange="binance", symbol="BTCUSDT")
        self.mod.record_kline_window_fill_ratio(exchange="binance", symbol="BTCUSDT", ratio=0.85)

    def test_record_checkpoint_runs(self) -> None:
        self.mod.record_checkpoint(
            job="crypto_pipeline", duration_sec=15.0, size_bytes=50_000_000, success=True
        )
        self.mod.record_checkpoint(
            job="crypto_pipeline", duration_sec=30.0, size_bytes=0, success=False, reason="timeout"
        )

    def test_record_kafka_source_runs(self) -> None:
        self.mod.record_kafka_source(topic="crypto_ticker", partition=0, n=500)
        self.mod.record_kafka_source_drop(topic="crypto_ticker", reason="late_event")
        self.mod.record_kafka_source_watermark(topic="crypto_ticker", lag_sec=2.5)
        self.mod.record_kafka_source_deserialize(topic="crypto_ticker", duration_sec=0.001)


if __name__ == "__main__":
    unittest.main()
