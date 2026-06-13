"""
Standalone (no-pyflink) tests for the Flink writer metrics integration.

These tests work by directly invoking the writer metric helpers and
the in-process mock-writer shims, since pyflink is only available
inside the Flink TaskManager container — not in CI.

We verify all the helper functions and metric declarations from
``src/processing/writers/metrics.py`` emit Prometheus values with
the right labels and update the right time series.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from prometheus_client import CollectorRegistry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _fresh_registry() -> CollectorRegistry:
    """Drop the global registry's collectors and return a fresh one.

    We can't easily make Prometheus metrics bind to a custom registry
    in module-load time (because of the way ``prometheus_client.metrics``
    imports ``REGISTRY`` from ``prometheus_client.registry``), so the
    simplest path is to just clear the global registry before each
    module reload and use it as the test registry.
    """
    from prometheus_client import REGISTRY
    for collector in list(REGISTRY._names_to_collectors.values()):
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    return REGISTRY


def _load_flink_metrics():
    """Load writers/metrics.py with a freshly-cleaned global registry."""
    _fresh_registry()
    spec = importlib.util.spec_from_file_location(
        "flink_metrics_test", str(REPO_ROOT / "src" / "processing" / "writers" / "metrics.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _counter(registry: CollectorRegistry, name: str, **labels) -> float:
    total = 0.0
    # Accept both ``foo`` and ``foo_total`` as the metric name
    metric_name = name[:-len("_total")] if name.endswith("_total") else name
    for metric in registry.collect():
        if metric.name != metric_name:
            continue
        for sample in metric.samples:
            # Counter samples are exposed as ``<name>_total``; skip the
            # ``_created`` companion sample.
            if sample.name not in (metric_name, f"{metric_name}_total"):
                continue
            if labels and not all(sample.labels.get(k) == v for k, v in labels.items()):
                continue
            total += sample.value
    return total


def _gauge(registry: CollectorRegistry, name: str, **labels) -> float:
    total = 0.0
    # Accept both ``foo`` and ``foo_total`` (in case the caller
    # mistakenly appends the suffix — gauges never get one in the
    # writer metrics module, but stay forgiving).
    metric_name = name[:-len("_total")] if name.endswith("_total") else name
    for metric in registry.collect():
        if metric.name != metric_name:
            continue
        for sample in metric.samples:
            if sample.name != metric_name:
                continue
            if labels and not all(sample.labels.get(k) == v for k, v in labels.items()):
                continue
            total += sample.value
    return total


def _histogram_count(registry: CollectorRegistry, name: str, **labels) -> float:
    total = 0.0
    for metric in registry.collect():
        if metric.name != name:
            continue
        for sample in metric.samples:
            if sample.name != f"{name}_count":
                continue
            if labels and not all(sample.labels.get(k) == v for k, v in labels.items()):
                continue
            total += sample.value
    return total


class _FreshModuleMixin:
    """Mixin that gives each test its own freshly-loaded metrics module.

    Using ``setUp`` ensures every test method starts from a clean
    registry and a fresh module so counters are not polluted by
    other tests in the class.
    """

    def setUp(self) -> None:
        self.registry = _fresh_registry()
        self.m = _load_flink_metrics()


class TestWriterMetricsIntegration(_FreshModuleMixin, unittest.TestCase):
    """End-to-end: drive the metric helpers and verify Prometheus output."""

    def test_record_flush_increments_all_writers(self) -> None:
        self.m.record_flush(
            writer="keydb_ticker", sink="redis",
            duration_sec=0.05, n_records=10, trigger="time",
        )
        self.assertGreater(_counter(self.registry, "flink_writer_flush_calls_total",
                                    writer="keydb_ticker", sink="redis", trigger="time"), 0)
        self.assertGreater(_counter(self.registry, "flink_writer_records_emitted_total",
                                    writer="keydb_ticker", sink="redis"), 0)
        self.assertGreater(_histogram_count(self.registry, "flink_writer_flush_duration_seconds",
                                            writer="keydb_ticker", sink="redis"), 0)
        self.assertGreater(_histogram_count(self.registry, "flink_writer_records_per_flush",
                                            writer="keydb_ticker", sink="redis"), 0)

    def test_record_flush_with_error_increments_errors(self) -> None:
        self.m.record_flush(
            writer="keydb_kline", sink="redis",
            duration_sec=0.5, n_records=20, trigger="size",
            error="ConnectionError",
        )
        self.assertGreater(_counter(self.registry, "flink_writer_errors_total",
                                    writer="keydb_kline", sink="redis",
                                    error_type="ConnectionError"), 0)

    def test_record_buffer_size_updates_gauge(self) -> None:
        self.m.record_buffer_size(writer="keydb_trade", sink="redis", size=42)
        self.assertEqual(_gauge(self.registry, "flink_writer_buffer_size",
                                writer="keydb_trade", sink="redis"), 42)

    def test_record_kafka_source(self) -> None:
        self.m.record_kafka_source(topic="crypto_ticker", partition=0, n=5)
        self.assertEqual(_counter(self.registry, "flink_kafka_source_records_in_total",
                                  topic="crypto_ticker", partition="0"), 5)

    def test_record_kafka_source_drop(self) -> None:
        self.m.record_kafka_source_drop(topic="crypto_klines", reason="late_event")
        self.assertEqual(_counter(self.registry, "flink_kafka_source_records_dropped_total",
                                  topic="crypto_klines", reason="late_event"), 1)

    def test_record_kafka_source_deserialize(self) -> None:
        self.m.record_kafka_source_deserialize(topic="crypto_ticker", duration_sec=0.002)
        self.assertGreater(_histogram_count(
            self.registry, "flink_kafka_source_deserialize_duration_seconds",
            topic="crypto_ticker",
        ), 0)

    def test_record_kafka_source_watermark(self) -> None:
        self.m.record_kafka_source_watermark(topic="crypto_ticker", lag_sec=2.5)
        self.assertEqual(_gauge(self.registry, "flink_kafka_source_watermark_lag_seconds",
                                topic="crypto_ticker"), 2.5)

    def test_record_writer_event_time(self) -> None:
        self.m.record_writer_event_time(
            writer="keydb_ticker", exchange="binance", symbol="BTCUSDT",
            event_ts=1700000000.0,
        )
        self.assertEqual(_gauge(self.registry, "flink_writer_last_event_timestamp_seconds",
                                writer="keydb_ticker", exchange="binance", symbol="BTCUSDT"),
                         1700000000.0)

    def test_record_writer_new_key(self) -> None:
        self.m.record_writer_new_key(writer="keydb_ticker", exchange="okx")
        self.assertEqual(_counter(self.registry, "flink_writer_keys",
                                  writer="keydb_ticker", exchange="okx"), 1)

    def test_record_indicator_recompute(self) -> None:
        self.m.record_indicator_recompute(indicator="rsi14", trigger="new_candle")
        self.m.record_indicator_recompute(indicator="rsi14", trigger="new_candle")
        self.m.record_indicator_recompute(indicator="macd", trigger="gap_fill")
        self.assertEqual(_counter(self.registry, "flink_indicator_recomputations_total",
                                  indicator="rsi14", trigger="new_candle"), 2)
        self.assertEqual(_counter(self.registry, "flink_indicator_recomputations_total",
                                  indicator="macd", trigger="gap_fill"), 1)

    def test_record_indicator_warmup(self) -> None:
        self.m.record_indicator_warmup(state_type="ema", duration_sec=2.5)
        self.m.record_indicator_warmup(state_type="ema", duration_sec=3.0)
        self.assertGreater(_histogram_count(
            self.registry, "flink_indicator_state_warmup_duration_seconds",
            state_type="ema",
        ), 0)

    def test_record_kline_gap_fill(self) -> None:
        self.m.record_kline_gap_fill(exchange="binance", symbol="ETHUSDT")
        self.m.record_kline_gap_fill(exchange="binance", symbol="ETHUSDT")
        self.m.record_kline_gap_fill(exchange="binance", symbol="ETHUSDT")
        self.assertEqual(_counter(self.registry, "flink_kline_gap_fills",
                                  exchange="binance", symbol="ETHUSDT"), 3)

    def test_record_kline_window_fill_ratio(self) -> None:
        self.m.record_kline_window_fill_ratio(exchange="binance", symbol="BTCUSDT", ratio=0.85)
        self.assertEqual(_gauge(self.registry, "flink_kline_window_fill_ratio",
                                exchange="binance", symbol="BTCUSDT"), 0.85)

    def test_record_checkpoint_success(self) -> None:
        self.m.record_checkpoint(
            job="crypto_pipeline", duration_sec=12.0, size_bytes=50_000_000, success=True,
        )
        self.assertEqual(_counter(self.registry, "flink_checkpoint_success_total",
                                  job="crypto_pipeline"), 1)
        self.assertEqual(_gauge(self.registry, "flink_checkpoint_size_bytes",
                                job="crypto_pipeline"), 50_000_000)
        self.assertGreater(_histogram_count(
            self.registry, "flink_checkpoint_duration_seconds",
            job="crypto_pipeline", result="success",
        ), 0)

    def test_record_checkpoint_failure(self) -> None:
        self.m.record_checkpoint(
            job="crypto_pipeline", duration_sec=120.0, size_bytes=0,
            success=False, reason="timeout",
        )
        self.assertEqual(_counter(self.registry, "flink_checkpoint_failures_total",
                                  job="crypto_pipeline", reason="timeout"), 1)
        self.assertGreater(_histogram_count(
            self.registry, "flink_checkpoint_duration_seconds",
            job="crypto_pipeline", result="failure",
        ), 0)

    def test_init_metrics_seeds_zero_gauges(self) -> None:
        self.m.init_metrics()
        # All 8 writers × 2 sinks (16 combinations) should be 0
        for writer in ("keydb_ticker", "keydb_kline", "keydb_trade", "keydb_depth",
                       "influxdb_ticker", "influxdb_kline", "indicator", "kline_aggregator"):
            for sink in ("redis", "influxdb"):
                v = _gauge(self.registry, "flink_writer_buffer_size", writer=writer, sink=sink)
                self.assertEqual(v, 0.0, f"Buffer for {writer}/{sink} should be 0 after init")
        # And indicator state types
        for state_type in ("ema", "rsi", "bb", "macd", "macd_signal",
                           "candle_deque", "closes_deque", "volumes_deque"):
            v = _gauge(self.registry, "flink_indicator_state_keys", state_type=state_type)
            self.assertEqual(v, 0.0, f"State {state_type} should be 0 after init")

    def test_init_metrics_is_idempotent(self) -> None:
        self.m.init_metrics()
        self.m.init_metrics()
        # If we reach here without error, idempotency holds

    def test_record_backpressure_and_inflight(self) -> None:
        self.m.record_backpressure(
            job="crypto_pipeline", subtask="0", operator="kafka_source", ms_per_sec=150.0,
        )
        self.m.record_inflight(
            job="crypto_pipeline", subtask="0", operator="kafka_source", count=42,
        )
        self.assertEqual(_gauge(self.registry, "flink_operator_backpressure_ms_per_second",
                                job="crypto_pipeline", subtask="0", operator="kafka_source"),
                         150.0)
        self.assertEqual(_gauge(self.registry, "flink_operator_inflight_records",
                                job="crypto_pipeline", subtask="0", operator="kafka_source"),
                         42)

    def test_all_declared_metrics_have_unique_names(self) -> None:
        names = [metric.name for metric in self.registry.collect()]
        self.assertEqual(len(names), len(set(names)), "Duplicate metric names registered")


class TestWriterMetricsLabelTaxonomy(_FreshModuleMixin, unittest.TestCase):
    """Verify the label taxonomy matches the alert / dashboard definitions."""

    def test_sink_label_set(self) -> None:
        self.m.init_metrics()
        for metric in self.registry.collect():
            if metric.name in ("flink_writer_buffer_size", "flink_writer_flush_duration_seconds"):
                for sample in metric.samples:
                    if "sink" in sample.labels:
                        self.assertIn(
                            sample.labels["sink"], {"redis", "influxdb"},
                            f"Unexpected sink label: {sample.labels['sink']}",
                        )

    def test_trigger_label_set(self) -> None:
        for trigger in ("size", "time", "close", "inline"):
            self.m.record_flush("keydb_ticker", "redis", 0.01, 1, trigger=trigger)
        # If we get here without error, all 4 trigger labels were accepted

    def test_writers_and_state_types_covered(self) -> None:
        self.m.init_metrics()
        declared_writers = set()
        for metric in self.registry.collect():
            if metric.name in ("flink_writer_buffer_size", "flink_writer_flush_duration_seconds"):
                for sample in metric.samples:
                    if "writer" in sample.labels:
                        declared_writers.add(sample.labels["writer"])
        expected = {"keydb_ticker", "keydb_kline", "keydb_trade", "keydb_depth",
                    "influxdb_ticker", "influxdb_kline", "indicator", "kline_aggregator"}
        missing = expected - declared_writers
        self.assertFalse(missing, f"Missing writers in metrics: {missing}")


if __name__ == "__main__":
    unittest.main()
