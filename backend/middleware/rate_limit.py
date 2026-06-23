"""
Lightweight in-process rate limiter for FastAPI.

Implements A10.2 (``API rate limit hit``) in
``docs/dataflow_analysis_and_observability_plan.md``.

Why in-process
--------------
* The production deployment sits behind an Nginx reverse proxy that
  already enforces a per-IP rate limit. This middleware is a defence
  in depth for cases where Nginx is bypassed (dev mode, k6 tests).
* A distributed token-bucket (Redis) is the proper long-term answer
  but is out of Phase 5 scope.

How it works
------------
* Per-IP sliding window of 60 seconds. Default 200 requests / minute
  per IP. Configurable via env: ``RATE_LIMIT_PER_MINUTE``.
* When a request exceeds the limit, we return ``429 Too Many Requests``
  and increment ``api_rate_limited_total{ip=`` hash only for privacy ``}``
  so dashboards/alerting can see who's getting throttled.
* The IP hash is a SHA-256 prefix to avoid logging raw IPs in metric
  labels (privacy).
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("backend.middleware.rate_limit")


def _ip_hash(ip: str) -> str:
    """Return a short hash of the client IP for privacy-preserving
    metric labels. We don't want raw IPs showing up in Prometheus."""
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:12]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter.

    Args:
        app: the ASGI application to wrap.
        per_minute: max requests per 60-second window per IP.
        exempt_paths: set of path prefixes to never throttle (e.g.
            ``/metrics``, ``/health``).
    """

    def __init__(
        self,
        app,
        per_minute: int | None = None,
        exempt_paths: tuple[str, ...] = (
            "/metrics",
            "/health",
            "/api/health",
            "/api/rum",
            "/docs",
            "/openapi.json",
        ),
    ) -> None:
        super().__init__(app)
        self.per_minute = per_minute or int(os.environ.get("RATE_LIMIT_PER_MINUTE", "1200"))
        self.exempt_paths = exempt_paths
        # window: IP -> deque of request timestamps
        self._window: Dict[str, Deque[float]] = defaultdict(deque)
        # Lazy-import the counter so the middleware can be loaded
        # even when ``backend.api.metrics`` hasn't been imported yet.
        from backend.api.metrics import API_RATE_LIMITED_TOTAL
        self._counter = API_RATE_LIMITED_TOTAL

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._window[ip]
        cutoff = now - 60.0
        # Drop entries outside the window
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.per_minute:
            self._counter.labels(ip_hash=_ip_hash(ip), path=path).inc()
            logger.info(
                "Rate-limited request from %s on %s (limit=%d/min)",
                ip, path, self.per_minute,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "message": f"Limit is {self.per_minute} requests/minute/IP",
                    "retry_after_seconds": 60,
                },
                headers={"Retry-After": "60"},
            )
        window.append(now)
        return await call_next(request)


# Module-level counter — defined here so the middleware can import it
# before ``backend.api.metrics`` is loaded in the app boot order.
def _ensure_counter():
    """Lazily create the counter from ``backend.api.metrics`` if the
    module hasn't been imported yet. We re-export the labels for
    callers that need to read the current value."""
    from backend.api.metrics import API_RATE_LIMITED_TOTAL
    return API_RATE_LIMITED_TOTAL
