"""Tests for B7 indicator state persistence (Redis-backed)."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from collections import deque
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


class _FakeRedis:
    """Minimal in-process replacement for the Redis client.

    We don't want real Redis in unit tests — the writer only uses
    ``set`` / ``get`` / ``scan_iter`` / ``pipeline``, all of which
    are easy to fake.
    """

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.pipelined_calls: int = 0

    def set(self, key, value, ex=None):
        self.kv[key] = value

    def get(self, key):
        return self.kv.get(key)

    def scan_iter(self, match="*", count=100):
        # Crude match: only support ``prefix:*`` style.
        prefix = match.rstrip("*")
        for k in self.kv.keys():
            if k.startswith(prefix):
                yield k

    def pipeline(self, transaction=False):
        parent = self

        class _Pipe:
            def __init__(self):
                self._ops: list = []

            def set(self, key, value, ex=None):
                self._ops.append((key, value))

            def execute(self):
                parent.pipelined_calls += 1
                for k, v in self._ops:
                    parent.kv[k] = v

        return _Pipe()


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, str(REPO / relpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeWriter:
    """Mimics the state dicts IndicatorWriter maintains."""

    MAX_HISTORY = 60

    def __init__(self) -> None:
        self._closes: dict[str, deque] = {}
        self._volumes: dict[str, deque] = {}
        self._candles: dict[str, deque] = {}
        self._ema_state: dict[str, dict[int, float]] = {}
        self._macd_signal_state: dict[str, float] = {}


class TestIndicatorStateStore:
    def setup_method(self):
        # Clean registry to avoid duplicate-registration from other
        # test files in this directory.
        from prometheus_client import REGISTRY
        for c in list(REGISTRY._names_to_collectors.values()):
            try:
                REGISTRY.unregister(c)
            except Exception:
                pass
        # Re-load writers.metrics and indicator_state under canonical
        # names so the store can find the helper functions.
        sys.modules.pop("writers.metrics", None)
        sys.modules.pop("writers.indicator_state", None)
        self.writers_metrics = _load(
            "writers.metrics", "src/processing/writers/metrics.py"
        )
        self.store_mod = _load(
            "writers.indicator_state",
            "src/processing/writers/indicator_state.py",
        )

    def test_save_then_load_roundtrip(self):
        r = _FakeRedis()
        store = self.store_mod.IndicatorStateStore(r)
        store.save(
            "binance", "BTCUSDT",
            {"closes": [100, 101, 102], "ema_state": {"12": 101.5}},
        )
        loaded = store.load("binance", "BTCUSDT")
        assert loaded == {"closes": [100, 101, 102], "ema_state": {"12": 101.5}}

    def test_save_batch_uses_pipeline(self):
        r = _FakeRedis()
        store = self.store_mod.IndicatorStateStore(r)
        store.save_batch(
            "binance",
            {
                "BTCUSDT": {"closes": [1, 2]},
                "ETHUSDT": {"closes": [3, 4]},
                "ADAUSDT": {"closes": [5, 6]},
            },
        )
        assert r.pipelined_calls == 1
        assert store.load("binance", "BTCUSDT") == {"closes": [1, 2]}
        assert store.load("binance", "ETHUSDT") == {"closes": [3, 4]}
        assert store.load("binance", "ADAUSDT") == {"closes": [5, 6]}

    def test_save_tolerates_redis_failure(self):
        class _Boom:
            def set(self, *args, **kwargs):
                raise RuntimeError("simulated Redis outage")

        store = self.store_mod.IndicatorStateStore(_Boom())
        # Should NOT raise — graceful degradation.
        store.save("binance", "BTCUSDT", {"closes": [1]})

    def test_load_returns_none_on_missing(self):
        store = self.store_mod.IndicatorStateStore(_FakeRedis())
        assert store.load("binance", "BTCUSDT") is None

    def test_hydrate_writer_restores_state(self):
        """B7's main payoff: a writer instance can be re-built from
        the persisted snapshot without going back to Kafka."""
        r = _FakeRedis()
        store = self.store_mod.IndicatorStateStore(r)
        # Simulate a previous run that persisted state.
        store.save(
            "binance", "BTCUSDT",
            {
                "closes": [100, 101, 102, 103],
                "volumes": [10, 11, 12, 13],
                "candles": [{"o": 100, "c": 103}],
                "ema_state": {"12": 102.0, "26": 101.5},
                "macd_signal_state": 1.5,
            },
        )
        # Now spin up a fresh writer and hydrate it.
        w = _FakeWriter()
        n = store.hydrate_writer(w, "binance")
        assert n == 1
        assert list(w._closes["BTCUSDT"]) == [100, 101, 102, 103]
        assert list(w._volumes["BTCUSDT"]) == [10, 11, 12, 13]
        assert w._ema_state["BTCUSDT"] == {12: 102.0, 26: 101.5}
        assert w._macd_signal_state["BTCUSDT"] == 1.5

    def test_snapshot_writer_captures_all_dicts(self):
        w = _FakeWriter()
        w._closes["BTCUSDT"] = deque([1, 2, 3], maxlen=60)
        w._volumes["BTCUSDT"] = deque([10, 20, 30], maxlen=60)
        w._candles["BTCUSDT"] = deque([{"o": 1, "c": 2}], maxlen=60)
        w._ema_state["BTCUSDT"] = {12: 2.5}
        w._macd_signal_state["BTCUSDT"] = 0.5
        store = self.store_mod.IndicatorStateStore(_FakeRedis())
        snap = store.snapshot_writer(w)
        assert "BTCUSDT" in snap
        assert snap["BTCUSDT"]["closes"] == [1, 2, 3]
        assert snap["BTCUSDT"]["volumes"] == [10, 20, 30]
        # EMA keys must be stringified for JSON.
        assert snap["BTCUSDT"]["ema_state"] == {"12": 2.5}
        assert snap["BTCUSDT"]["macd_signal_state"] == 0.5
        assert "saved_at" in snap["BTCUSDT"]

    def test_round_trip_via_snapshot_then_hydrate(self):
        """End-to-end: writer A computes, writer B (fresh) hydrates."""
        r = _FakeRedis()
        store_w = self.store_mod.IndicatorStateStore(r)

        # Writer A emits some state.
        w_a = _FakeWriter()
        w_a._closes["ETHUSDT"] = deque([1, 2, 3, 4, 5], maxlen=60)
        w_a._ema_state["ETHUSDT"] = {12: 3.0, 26: 2.5}
        w_a._macd_signal_state["ETHUSDT"] = 0.1
        store_w.save_batch("binance", store_w.snapshot_writer(w_a))

        # Writer B starts up after a Flink restart and rehydrates.
        w_b = _FakeWriter()
        n = store_w.hydrate_writer(w_b, "binance")
        assert n == 1
        assert list(w_b._closes["ETHUSDT"]) == [1, 2, 3, 4, 5]
        assert w_b._ema_state["ETHUSDT"] == {12: 3.0, 26: 2.5}
        assert w_b._macd_signal_state["ETHUSDT"] == 0.1

    def test_hydrate_skips_corrupt_payload(self):
        r = _FakeRedis()
        r.kv["indicator:state:binance:BAD"] = "{not valid json"
        store = self.store_mod.IndicatorStateStore(r)
        w = _FakeWriter()
        n = store.hydrate_writer(w, "binance")
        assert n == 0  # corrupt entry is dropped, no crash
        assert w._closes == {}

    def test_hydrate_warmup_metric_is_recorded(self):
        r = _FakeRedis()
        store = self.store_mod.IndicatorStateStore(r)
        w = _FakeWriter()
        w._closes["BTCUSDT"] = deque([1.0], maxlen=60)
        store.save("binance", "BTCUSDT", {"closes": [1.0]})
        store.hydrate_writer(w, "binance")
        # The metric should have ticked at least once.
        from prometheus_client import REGISTRY
        n = 0.0
        for m in REGISTRY.collect():
            if m.name == "flink_indicator_state_warmup_duration_seconds":
                for s in m.samples:
                    if s.name.endswith("_count"):
                        n += float(s.value)
        assert n >= 1.0
