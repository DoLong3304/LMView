"""Tests for the X-Request-Id middleware."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent.parent


def _build_app():
    """Build a fresh FastAPI app with the request-id middleware.

    We reload the metrics module so that the API_REQUEST_ID_SAMPLES
    counter is freshly registered (other test files clear the
    registry between runs).
    """
    from prometheus_client import REGISTRY
    for c in list(REGISTRY._names_to_collectors.values()):
        try:
            REGISTRY.unregister(c)
        except Exception:
            pass
    sys.modules.pop("backend.api.metrics", None)
    spec = importlib.util.spec_from_file_location(
        "backend.api.metrics", str(REPO / "backend" / "api" / "metrics.py")
    )
    metrics = importlib.util.module_from_spec(spec)
    sys.modules["backend.api.metrics"] = metrics
    spec.loader.exec_module(metrics)

    sys.modules.pop("common.logging", None)
    spec2 = importlib.util.spec_from_file_location(
        "common.logging", str(REPO / "src" / "common" / "logging.py")
    )
    cl = importlib.util.module_from_spec(spec2)
    sys.modules["common.logging"] = cl
    spec2.loader.exec_module(cl)
    # Configure plain-text logging so we can grep the stream
    cl.setup_logging("test", level=logging.DEBUG, json=False)

    sys.modules.pop("backend.middleware.request_id", None)
    spec3 = importlib.util.spec_from_file_location(
        "backend.middleware.request_id",
        str(REPO / "backend" / "middleware" / "request_id.py"),
    )
    rid_mod = importlib.util.module_from_spec(spec3)
    sys.modules["backend.middleware.request_id"] = rid_mod
    spec3.loader.exec_module(rid_mod)

    app = FastAPI()

    @app.get("/api/ping")
    async def ping():
        # Reading the request-id from inside the handler
        # confirms the contextvar was set.
        from common.logging import current_request_id
        return {"rid": current_request_id()}

    @app.get("/api/boom")
    async def boom():
        raise RuntimeError("simulated failure")

    app.add_middleware(rid_mod.RequestIdMiddleware)
    return app, metrics, cl


import logging  # placed at top for ruff


class TestRequestIdMiddleware:
    def test_generates_id_when_missing(self):
        app, _, _ = _build_app()
        with TestClient(app) as c:
            r = c.get("/api/ping")
            assert r.status_code == 200
            rid = r.headers.get("X-Request-Id")
            assert rid is not None
            assert len(rid) == 12  # default generator
            assert int(rid, 16)  # all hex

    def test_echoes_incoming_id(self):
        app, _, _ = _build_app()
        with TestClient(app) as c:
            r = c.get("/api/ping", headers={"X-Request-Id": "my-test-12345"})
            assert r.headers["X-Request-Id"] == "my-test-12345"
            # The handler saw the same id via the contextvar.
            assert r.json() == {"rid": "my-test-12345"}

    def test_unique_id_per_request(self):
        app, _, _ = _build_app()
        with TestClient(app) as c:
            ids = set()
            for _ in range(5):
                r = c.get("/api/ping")
                ids.add(r.headers["X-Request-Id"])
            assert len(ids) == 5  # all different

    def test_truncates_oversized_id(self):
        app, _, _ = _build_app()
        with TestClient(app) as c:
            giant = "x" * 1000
            r = c.get("/api/ping", headers={"X-Request-Id": giant})
            assert len(r.headers["X-Request-Id"]) <= 64

    def test_5xx_still_returns_rid_header(self):
        app, _, _ = _build_app()
        # We need an exception handler so TestClient can
        # serve the 500 response through the middleware.
        from fastapi.responses import JSONResponse
        @app.exception_handler(RuntimeError)
        async def _h(_req, exc):
            return JSONResponse({"error": str(exc)}, status_code=500)

        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/api/boom")
            assert r.status_code == 500
            assert "X-Request-Id" in r.headers

    def test_metric_recorded_per_request(self):
        app, metrics, _ = _build_app()
        with TestClient(app) as c:
            c.get("/api/ping")
            c.get("/api/ping", headers={"X-Request-Id": "another-id"})

        # API_REQUEST_ID_SAMPLES counter should have ticked at
        # least twice (one per call). We look at the ``_total``
        # suffix which is what prometheus_client emits for
        # Counter samples.
        from prometheus_client import REGISTRY
        total = 0.0
        for m in REGISTRY.collect():
            if m.name == "api_request_id_samples":
                for s in m.samples:
                    if s.name == "api_request_id_samples_total":
                        total += float(s.value)
        assert total >= 2.0

    def test_rid_is_hashed_not_stored_raw(self):
        """Privacy: the metric label must use a hash, not the
        full id, to keep cardinality bounded."""
        app, metrics, _ = _build_app()
        with TestClient(app) as c:
            c.get("/api/ping", headers={"X-Request-Id": "leak-me-please"})

        from prometheus_client import REGISTRY
        for m in REGISTRY.collect():
            if m.name != "api_request_id_samples":
                continue
            for s in m.samples:
                rid_hash = s.labels.get("rid_hash", "")
                if rid_hash:
                    # Must NOT contain the raw incoming id
                    assert "leak" not in rid_hash
                    # Must be 12 chars (sha256[:12])
                    assert len(rid_hash) == 12
                    int(rid_hash, 16)  # hex
