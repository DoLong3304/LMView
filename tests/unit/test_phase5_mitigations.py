"""
Tests for the bottleneck-mitigation code added in Phase 5 step 2.

This covers:
- B1:  Producer dedup lock (race condition)
- B5:  Reduced flush intervals on keydb_ticker / keydb_trades
- B6:  Reduced checkpoint interval (60s) in pipeline.py
- B11: Trino metrics helpers (query duration, active count, fallback)

All tests use the standard pytest + clean-registry pattern that the
other Phase 5 metric tests use (see ``test_phase5_metrics.py``).
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

from prometheus_client import REGISTRY

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fresh_registry():
    for c in list(REGISTRY._names_to_collectors.values()):
        try:
            REGISTRY.unregister(c)
        except Exception:
            pass


def _load(name: str, rel_path: str):
    _fresh_registry()
    spec = importlib.util.spec_from_file_location(name, str(REPO_ROOT / rel_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _value(metric_name: str, **labels) -> float:
    """Sum a counter or gauge by name and label filter.

    The caller may pass:
    - Bare counter / gauge: ``my_metric`` — sums the single sample
    - Counter ``_total`` alias: ``my_metric_total`` — same as above
    - Histogram aggregate: ``my_metric_count`` / ``_sum`` / ``_bucket``
    """
    # Resolve to the underlying metric name
    base = metric_name
    if base.endswith("_total"):
        base = base[: -len("_total")]
    for suffix in ("_count", "_sum", "_bucket", "_created"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    # Determine the target sample name(s) to count.
    # If the caller passed an aggregate suffix, only count that sample.
    # If the caller passed the bare name, count whatever sample variants
    # exist for this metric (``<base>`` for gauges, ``<base>_total`` for
    # counters, ``<base>_count``/``<base>_sum``/``<base>_bucket`` for
    # histograms).
    target_samples: tuple[str, ...]
    if metric_name == base:
        # Bare name: collect all known sample variants
        target_samples = (base, f"{base}_total", f"{base}_count",
                          f"{base}_sum", f"{base}_bucket")
    elif metric_name.endswith("_total"):
        target_samples = (f"{base}_total",)
    elif metric_name.endswith(("_count", "_sum", "_bucket", "_created")):
        target_samples = (metric_name,)
    else:
        target_samples = (metric_name,)

    total = 0.0
    for metric in REGISTRY.collect():
        if metric.name != base:
            continue
        for sample in metric.samples:
            if sample.name not in target_samples:
                continue
            if labels and not all(sample.labels.get(k) == v for k, v in labels.items()):
                continue
            total += sample.value
    return total


# ─────────────────────────────────────────────────────────────────────────────
# B1 — Producer dedup lock
# ─────────────────────────────────────────────────────────────────────────────

class TestB1DedupLock(unittest.TestCase):
    """B1: ticker dedup dicts are protected by a threading.Lock."""

    def setUp(self) -> None:
        self.path = REPO_ROOT / "src" / "producer" / "main.py"
        self.text = self.path.read_text(encoding="utf-8")

    def test_dedup_lock_defined(self) -> None:
        self.assertRegex(
            self.text, r"_dedup_lock\s*=\s*threading\.Lock\(\)",
            "Producer must define a threading.Lock for dedup state",
        )

    def test_handle_ticker_uses_lock(self) -> None:
        """The check-then-set sequence must be wrapped in ``with _dedup_lock:``."""
        # The lock acquisition must occur inside handle_ticker_message
        # and must wrap both the ``_last_close`` and ``_last_sent_ts``
        # writes.
        match = re.search(
            r"def\s+handle_ticker_message\b.*?(?=\ndef\s|\Z)",
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "handle_ticker_message not found")
        body = match.group(0)
        self.assertIn("_dedup_lock", body,
                      "handle_ticker_message must reference _dedup_lock")
        # The lock must be entered with the ``with`` statement
        self.assertIn("with _dedup_lock", body,
                      "handle_ticker_message must use ``with _dedup_lock:``")
        # And both dicts must be written inside the critical section.
        # Use re.search with DOTALL so ``.*`` can span newlines.
        self.assertIsNotNone(
            re.search(r"with _dedup_lock:.*_last_close\[symbol\]\s*=\s*cur",
                      body, re.DOTALL),
            "_last_close assignment must be inside the lock",
        )
        self.assertIsNotNone(
            re.search(r"with _dedup_lock:.*_last_sent_ts\[symbol\]\s*=\s*now",
                      body, re.DOTALL),
            "_last_sent_ts assignment must be inside the lock",
        )

    def test_threading_import(self) -> None:
        # ``import threading`` may be anywhere in the file; we look for
        # the import statement itself, not anchored to line start.
        self.assertRegex(self.text, r"(?m)^import threading$",
                         "main.py must import threading for the lock")


# ─────────────────────────────────────────────────────────────────────────────
# B5 — Reduced flush intervals
# ─────────────────────────────────────────────────────────────────────────────

class TestB5FlushInterval(unittest.TestCase):

    def test_keydb_ticker_flush_200ms(self) -> None:
        text = (REPO_ROOT / "src" / "processing" / "writers" / "keydb_ticker.py").read_text(encoding="utf-8")
        match = re.search(r"FLUSH_INTERVAL\s*=\s*([0-9.]+)", text)
        self.assertIsNotNone(match, "keydb_ticker.FLUSH_INTERVAL not found")
        value = float(match.group(1))
        self.assertLessEqual(value, 0.3,
                             f"keydb_ticker.FLUSH_INTERVAL={value} should be <= 0.3s after B5 fix")
        # B5 fix comment should be present
        self.assertIn("B5 fix", text, "keydb_ticker should document the B5 fix")

    def test_keydb_trades_flush_200ms(self) -> None:
        text = (REPO_ROOT / "src" / "processing" / "writers" / "keydb_trades.py").read_text(encoding="utf-8")
        match = re.search(r"FLUSH_INTERVAL\s*=\s*([0-9.]+)", text)
        self.assertIsNotNone(match, "keydb_trades.FLUSH_INTERVAL not found")
        value = float(match.group(1))
        self.assertLessEqual(value, 0.3,
                             f"keydb_trades.FLUSH_INTERVAL={value} should be <= 0.3s after B5 fix")
        self.assertIn("B5 fix", text, "keydb_trades should document the B5 fix")

    def test_keydb_kline_flush_100ms(self) -> None:
        """kline was already at 100ms in the original code; make sure we didn't regress."""
        text = (REPO_ROOT / "src" / "processing" / "writers" / "keydb_kline.py").read_text(encoding="utf-8")
        match = re.search(r"FLUSH_INTERVAL\s*=\s*([0-9.]+)", text)
        self.assertIsNotNone(match)
        value = float(match.group(1))
        self.assertLessEqual(value, 0.2,
                             f"keydb_kline.FLUSH_INTERVAL={value} should be <= 0.2s")


# ─────────────────────────────────────────────────────────────────────────────
# B6 — Checkpoint interval
# ─────────────────────────────────────────────────────────────────────────────

class TestB6CheckpointInterval(unittest.TestCase):

    def test_checkpoint_60s(self) -> None:
        text = (REPO_ROOT / "src" / "processing" / "pipeline.py").read_text(encoding="utf-8")
        # The interval is in milliseconds
        match = re.search(r"env\.enable_checkpointing\(\s*(\d[\d_]*)\s*\)", text)
        self.assertIsNotNone(match, "enable_checkpointing call not found")
        ms = int(match.group(1).replace("_", ""))
        self.assertEqual(ms, 60_000,
                         f"Checkpoint interval should be 60_000ms (B6 fix); got {ms}ms")
        self.assertIn("B6 fix", text, "pipeline.py should document the B6 fix")


# ─────────────────────────────────────────────────────────────────────────────
# B11 — Trino metrics
# ─────────────────────────────────────────────────────────────────────────────

class TestB11TrinoMetrics(unittest.TestCase):

    def setUp(self) -> None:
        self.m = _load("b11_metrics", "backend/api/metrics.py")

    def test_trino_query_duration_recorded(self) -> None:
        self.m.record_trino_query("market_summary", 0.42, success=True)
        # B11: query_type label slice must exist
        v = _value("backend_trino_query_duration_seconds_count",
                   query_type="market_summary", result="success")
        # Use the histogram ``_sum`` field to verify observation, since
        # ``_count`` is on the metric object but its sample name keeps
        # the bare metric prefix here.
        v_sum = _value("backend_trino_query_duration_seconds_sum",
                       query_type="market_summary", result="success")
        self.assertGreater(v_sum, 0, "Successful Trino query should be observed in histogram sum")

    def test_trino_failure_recorded(self) -> None:
        self.m.record_trino_query("top_movers_gainer", 1.5, success=False,
                                  reason="TrinoExternalError")
        v = _value("backend_trino_query_failures",
                   query_type="top_movers_gainer", reason="TrinoExternalError")
        self.assertGreater(v, 0, "Failed Trino query should increment failure counter")
        v_dur = _value("backend_trino_query_duration_seconds_sum",
                       query_type="top_movers_gainer", result="failure")
        self.assertGreater(v_dur, 0,
                           "Failed Trino query should also populate the duration histogram")

    def test_trino_active_queries_gauge(self) -> None:
        """The gauge should be readable (even if no queries are in flight)."""
        self.assertTrue(hasattr(self.m, "TRINO_ACTIVE_QUERIES"))
        # A gauge, not a counter — should be settable
        self.m.TRINO_ACTIVE_QUERIES.set(7)
        v = _value("backend_trino_active_queries")
        self.assertEqual(v, 7)
        self.m.TRINO_ACTIVE_QUERIES.set(0)

    def test_trino_fallback_recorded(self) -> None:
        self.m.record_trino_fallback("market_overview", "gold_empty_or_stale")
        v = _value("backend_trino_fallback",
                   endpoint="market_overview", reason="gold_empty_or_stale")
        self.assertGreater(v, 0, "Trino fallback should be recorded")

    def test_market_overview_imports_trino_helpers(self) -> None:
        """market_overview.py must import and use the Trino metric helpers."""
        text = (REPO_ROOT / "backend" / "api" / "market_overview.py").read_text(encoding="utf-8")
        self.assertIn("record_trino_query", text,
                      "market_overview.py must use record_trino_query")
        self.assertIn("record_trino_fallback", text,
                      "market_overview.py must use record_trino_fallback")
        self.assertIn("TRINO_ACTIVE_QUERIES", text,
                      "market_overview.py must use TRINO_ACTIVE_QUERIES")
        # Every fetch_one/fetch_all call should pass a query_type label
        for call in re.findall(r"trino\.fetch_(?:one|all)\([^)]+\)", text):
            self.assertIn("query_type=", call,
                          f"Trino call missing query_type label: {call!r}")


if __name__ == "__main__":
    unittest.main()
