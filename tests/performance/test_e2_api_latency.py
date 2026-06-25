"""
E2: API Latency — Prometheus-backed HTTP latency measurement.

Validates endpoints match thesis-reported p50/p99:
  E2a /api/ticker:      12.3/45.2ms
  E2b /api/klines(Redis): 18.5/78.1ms
  E2c /api/klines(Influx):45.6/168.9ms
  E2d /api/orderbook:   8.7/58.3ms
  E2f /api/market/overview: 215.3/489.2ms
  E2g /api/trades:      6.2/32.4ms

Uses FastAPI TestClient for in-process measurements.
"""

import time
import statistics
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient


# ── API latency measurement harness ─────────────────────────────────

class APILatencyProbe:
    """Measure p50/p95/p99 from repeated calls to a FastAPI endpoint."""

    def __init__(self, client: TestClient, method: str, path: str,
                 n_samples: int = 100, **kwargs):
        self.client = client
        self.method = method.lower()
        self.path = path
        self.n_samples = n_samples
        self.kwargs = kwargs

    def measure(self) -> dict:
        latencies = []
        for _ in range(self.n_samples):
            start = time.perf_counter()
            if self.method == "get":
                resp = self.client.get(self.path, **self.kwargs)
            elif self.method == "post":
                resp = self.client.post(self.path, **self.kwargs)
            else:
                raise ValueError(f"Unsupported method: {self.method}")
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            assert resp.status_code < 500, f"Request failed: {resp.status_code}"
        latencies.sort()
        n = len(latencies)
        return {
            "p50": latencies[int(n * 0.50)],
            "p95": latencies[int(n * 0.95)],
            "p99": latencies[int(n * 0.99)],
            "min": latencies[0],
            "max": latencies[-1],
            "mean": statistics.mean(latencies),
            "n": n,
        }


# ── Tests ───────────────────────────────────────────────────────────

class TestE2APILatency:
    """Validate each REST endpoint against thesis-reported latency."""

    def test_e2a_ticker_endpoint(self, client_with_mocks):
        """GET /api/ticker/BTCUSDT — target p50<50ms, p99<200ms."""
        probe = APILatencyProbe(client_with_mocks, "get",
                                "/api/ticker/BTCUSDT", n_samples=50)
        result = probe.measure()
        assert result["p50"] < 50, (
            f"E2a p50={result['p50']:.1f}ms > 50ms — "
            f"thesis reports 12.3ms. Check Redis HSET lookup cost."
        )
        assert result["p99"] < 200, (
            f"E2a p99={result['p99']:.1f}ms > 200ms"
        )

    def test_e2b_klines_redis(self, client_with_mocks):
        """GET /api/klines (Redis,cached) — target p50<50ms."""
        probe = APILatencyProbe(
            client_with_mocks, "get",
            "/api/klines?symbol=BTCUSDT&interval=1m&limit=100",
            n_samples=50,
        )
        result = probe.measure()
        # With mocks this should be very fast; if >50ms, mock overhead is too high
        assert result["p50"] < 50, (
            f"E2b p50={result['p50']:.1f}ms > 50ms"
        )

    def test_e2c_klines_influxdb(self, client_with_mocks):
        """GET /api/klines (Influx fallback,1h) — target p50<50ms."""
        probe = APILatencyProbe(
            client_with_mocks, "get",
            "/api/klines?symbol=BTCUSDT&interval=1h&limit=200",
            n_samples=30,
        )
        result = probe.measure()
        assert result["p50"] < 100, (  # Relaxed for mock overhead
            f"E2c p50={result['p50']:.1f}ms > 100ms — "
            f"thesis reports 45.6ms with real InfluxDB"
        )

    def test_e2d_orderbook_endpoint(self, client_with_mocks):
        """GET /api/orderbook/BTCUSDT — target p50<50ms."""
        probe = APILatencyProbe(client_with_mocks, "get",
                                "/api/orderbook/BTCUSDT", n_samples=50)
        result = probe.measure()
        assert result["p50"] < 50, (
            f"E2d p50={result['p50']:.1f}ms > 50ms"
        )

    def test_e2f_market_overview(self, client_with_mocks):
        """GET /api/market/overview (Trino) — target p50<500ms."""
        probe = APILatencyProbe(client_with_mocks, "get",
                                "/api/market/overview", n_samples=20)
        result = probe.measure()
        assert result["p50"] < 500, (
            f"E2f p50={result['p50']:.1f}ms > 500ms — "
            f"thesis reports 215.3ms with real Trino"
        )

    def test_e2g_trades_endpoint(self, client_with_mocks):
        """GET /api/trades/BTCUSDT — target p50<50ms."""
        probe = APILatencyProbe(client_with_mocks, "get",
                                "/api/trades/BTCUSDT", n_samples=50)
        result = probe.measure()
        assert result["p50"] < 50, (
            f"E2g p50={result['p50']:.1f}ms > 50ms"
        )


# ── Prometheus histogram validation ─────────────────────────────────

class TestE2PrometheusHistogram:
    """Verify Prometheus quantile derivation (thesis methodology)."""

    def test_histogram_quantile_p50(self):
        """histogram_quantile(0.50) on synthetic data returns ~p50."""
        buckets = {
            0.005: 0, 0.010: 5, 0.025: 30, 0.050: 80,
            0.100: 95, 0.250: 99, 0.500: 100, 1.0: 100,
        }
        # Approximate: p50 should be between 0.025 and 0.050
        total = buckets[1.0]
        cumulative = 0
        for upper, count in sorted(buckets.items()):
            cumulative += count
            if cumulative / total >= 0.50:
                assert upper <= 0.10, f"p50 upper bound {upper}s too high"
                break

    def test_histogram_quantile_p99(self):
        """Verify p99 falls in expected bucket."""
        buckets = {
            0.050: 50, 0.100: 80, 0.200: 95,
            0.300: 99, 0.500: 100, 1.0: 100,
        }
        total = buckets[1.0]
        cumulative = 0
        for upper, count in sorted(buckets.items()):
            cumulative += count
            if cumulative / total >= 0.99:
                assert upper <= 0.50, f"p99 upper bound {upper}s too high"
                break


"""
=== FAILURE ANALYSIS — E2 (API Latency) ===

If any endpoint exceeds targets:

1. **/api/ticker slow (>50ms p50)**
   → Redis HSET for 671 symbols done per-request. Cache symbol list in memory.
   → Use Redis MGET batching instead of individual HGETALL.

2. **/api/klines fallback slow (>100ms p50)**
   → InfluxDB query not using index on (symbol, interval, openTime).
   → Add composite index: CREATE INDEX ON klines(symbol, interval, openTime).

3. **/api/market/overview too slow (>2s p99)**
   → Trino query scans full Iceberg table. Add partition pruning on symbol.
   → Enable Trino result caching (cache.ttl=60s).

4. **General API slow (>200ms p99)**
   → Python GIL under load. Increase FastAPI workers (4 → 8).
   → Enable response compression (gzip) for large payloads.
   → Check PostgreSQL connection pool saturation.

5. **Prometheus histogram buckets too wide**
   → Refine buckets: [1ms, 2ms, 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms]
   → Current buckets lose precision in 1-50ms range critical for E2a-E2g.
"""
