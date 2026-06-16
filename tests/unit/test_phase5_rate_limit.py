"""Tests for A10.2 API rate-limit middleware.

The middleware lives at ``backend/middleware/rate_limit.py`` and
counts hits on ``api_rate_limited_total{ip_hash,path}`` for
clients that exceed ``RATE_LIMIT_PER_MINUTE`` requests per 60s
sliding window.
"""

from __future__ import annotations

import os

os.environ.setdefault("INFLUX_TOKEN", "fake")
os.environ.setdefault("INFLUX_URL", "http://localhost:8086")
os.environ.setdefault("INFLUX_ORG", "test")
os.environ.setdefault("INFLUX_BUCKET", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test")

import importlib
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


REPO = Path(__file__).resolve().parent.parent.parent


def _build_app(per_minute: int):
    """Build a fresh FastAPI app + rate-limit middleware, with all
    metrics modules loaded under canonical names so the test doesn't
    collide with other test files in this directory."""
    # Clean the registry to avoid duplicate-registration from the
    # other test files that import backend.api.metrics earlier.
    from prometheus_client import REGISTRY
    for c in list(REGISTRY._names_to_collectors.values()):
        try:
            REGISTRY.unregister(c)
        except Exception:
            pass

    # Drop the cached metrics module so the fresh registration wins.
    sys.modules.pop("backend.api.metrics", None)
    sys.modules.pop("backend.middleware.rate_limit", None)

    spec1 = importlib.util.spec_from_file_location(
        "backend.api.metrics", str(REPO / "backend" / "api" / "metrics.py")
    )
    metrics_mod = importlib.util.module_from_spec(spec1)
    sys.modules["backend.api.metrics"] = metrics_mod
    spec1.loader.exec_module(metrics_mod)

    spec2 = importlib.util.spec_from_file_location(
        "backend.middleware.rate_limit",
        str(REPO / "backend" / "middleware" / "rate_limit.py"),
    )
    rl_mod = importlib.util.module_from_spec(spec2)
    sys.modules["backend.middleware.rate_limit"] = rl_mod
    spec2.loader.exec_module(rl_mod)

    app = FastAPI()

    @app.get("/api/ping")
    async def ping():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    app.add_middleware(rl_mod.RateLimitMiddleware, per_minute=per_minute)
    return app, metrics_mod


def _count_rate_limited(metrics_mod, ip_hash: str | None = None, path: str | None = None) -> float:
    """Sum all ``api_rate_limited_total`` samples matching the filter."""
    from prometheus_client import REGISTRY
    total = 0.0
    for m in REGISTRY.collect():
        if m.name != "api_rate_limited":
            continue
        for s in m.samples:
            if s.name.endswith("_created"):
                continue
            if ip_hash is not None and s.labels.get("ip_hash") != ip_hash:
                continue
            if path is not None and s.labels.get("path") != path:
                continue
            total += float(s.value)
    return total


class TestRateLimitMiddleware:
    def test_under_limit_passes_through(self):
        app, _ = _build_app(per_minute=10)
        with TestClient(app) as c:
            for i in range(5):
                r = c.get("/api/ping")
                assert r.status_code == 200, f"call {i}: {r.status_code}"

    def test_over_limit_returns_429(self):
        app, metrics_mod = _build_app(per_minute=3)
        with TestClient(app) as c:
            for i in range(3):
                r = c.get("/api/ping")
                assert r.status_code == 200
            r = c.get("/api/ping")
            assert r.status_code == 429
            assert "Retry-After" in r.headers
            assert r.headers["Retry-After"] == "60"
            data = r.json()
            assert data["error"] == "rate_limited"
            assert "3 requests" in data["message"]

    def test_429_increments_metric(self):
        app, _ = _build_app(per_minute=2)
        with TestClient(app) as c:
            c.get("/api/ping")
            c.get("/api/ping")
            r = c.get("/api/ping")
            assert r.status_code == 429
        # Counter should reflect at least 1 throttled request
        v = _count_rate_limited(None, path="/api/ping")
        assert v >= 1.0

    def test_health_is_exempt(self):
        app, metrics_mod = _build_app(per_minute=1)
        with TestClient(app) as c:
            # exhaust the limit
            c.get("/api/ping")
            r = c.get("/api/ping")
            assert r.status_code == 429
            # /health is exempt
            for i in range(5):
                r = c.get("/health")
                assert r.status_code == 200, f"health call {i} should be exempt"

    def test_different_paths_share_quota(self):
        """The limiter tracks by IP, not by path. So ``/api/ping`` calls
        deplete the budget that ``/api/foo`` would otherwise use."""
        app = FastAPI()

        @app.get("/api/a")
        async def a():
            return {"a": 1}

        @app.get("/api/b")
        async def b():
            return {"b": 1}

        from prometheus_client import REGISTRY
        for c in list(REGISTRY._names_to_collectors.values()):
            try:
                REGISTRY.unregister(c)
            except Exception:
                pass
        sys.modules.pop("backend.api.metrics", None)
        sys.modules.pop("backend.middleware.rate_limit", None)
        spec1 = importlib.util.spec_from_file_location(
            "backend.api.metrics", str(REPO / "backend" / "api" / "metrics.py")
        )
        m1 = importlib.util.module_from_spec(spec1)
        sys.modules["backend.api.metrics"] = m1
        spec1.loader.exec_module(m1)
        spec2 = importlib.util.spec_from_file_location(
            "backend.middleware.rate_limit",
            str(REPO / "backend" / "middleware" / "rate_limit.py"),
        )
        m2 = importlib.util.module_from_spec(spec2)
        sys.modules["backend.middleware.rate_limit"] = m2
        spec2.loader.exec_module(m2)
        app.add_middleware(m2.RateLimitMiddleware, per_minute=2)

        with TestClient(app) as c:
            c.get("/api/a")
            c.get("/api/b")
            # 2 calls used, third call (any path) is throttled
            r = c.get("/api/a")
            assert r.status_code == 429

    def test_metric_uses_ip_hash_not_raw_ip(self):
        """Privacy: the metric label should NOT contain the raw IP."""
        app, _ = _build_app(per_minute=1)
        with TestClient(app) as c:
            c.get("/api/ping")
            r = c.get("/api/ping")
            assert r.status_code == 429

        from prometheus_client import REGISTRY
        for m in REGISTRY.collect():
            if m.name != "api_rate_limited":
                continue
            for s in m.samples:
                if s.name.endswith("_created"):
                    continue
                ip_hash = s.labels.get("ip_hash", "")
                # TestClient uses ``testclient`` as the host, so we
                # expect a 12-char hex hash, not the literal text.
                assert ip_hash != "testclient"
                assert len(ip_hash) == 12
                # All chars should be hex
                int(ip_hash, 16)  # raises if non-hex
