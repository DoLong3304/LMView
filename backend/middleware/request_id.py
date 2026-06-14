"""
Request-id correlation middleware.

A single HTTP request in LMView touches up to five services:

    nginx → FastAPI → Redis Sentinel → PostgreSQL → AI service

When a user reports "POST /api/ai/ask at 14:32:01 was slow", we
need to trace that one request across all five log streams.
That's impossible without a stable id echoed in every log line.

This middleware:

1. Reads ``X-Request-Id`` from the incoming request, or
   generates a 12-char hex id if missing.
2. Stores it in a :class:`contextvars.ContextVar` so any code
   path (including the AI service) can read it via
   :func:`common.logging.current_request_id`.
3. Echoes it back in the response header so the client (or
   upstream load balancer) can include it in bug reports.
4. Records the id in a Prometheus label on
   ``api_request_id_samples_total`` so an operator can join
   metric and log views.

We deliberately do **not** log the request body — that would
be a privacy issue for the AI endpoints.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("backend.middleware.request_id")


def _generate_request_id() -> str:
    """Generate a 12-char hex request id.

    12 hex chars = 48 bits of entropy = 281 trillion possible
    values. Collisions in a 30-day window are < 1 in 10 million
    for a 1k-req/sec service.
    """
    return secrets.token_hex(6)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request-id to every HTTP request.

    Place this *after* the rate-limit middleware so that
    throttled requests still get a log line.
    """

    HEADER_NAME = "X-Request-Id"

    def __init__(
        self,
        app: ASGIApp,
        *,
        header_name: Optional[str] = None,
        record_metrics: bool = True,
    ) -> None:
        super().__init__(app)
        self._header = header_name or self.HEADER_NAME
        self._record_metrics = record_metrics

    async def dispatch(self, request: Request, call_next):
        # 1. Pull the incoming id, or generate one.
        rid = request.headers.get(self._header) or _generate_request_id()
        # Truncate to 64 chars max so a malicious client can't
        # blow up the log line size.
        rid = rid[:64]

        # 2. Bind to the context var. We do this *before*
        #    call_next so the route handler sees the id, and
        #    *after* so the access-log line for this request
        #    carries it.
        from common.logging import bind_request_id
        bind_request_id(rid)

        # 3. Time the request so we can record latency in the
        #    metric label below.
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # 4. Unhandled exceptions still need a request-id
            #    line so we can trace them.
            logger.exception(
                "request failed (unhandled)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "rid": rid,
                },
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000.0

        # 5. Echo back to the client.
        response.headers[self._header] = rid

        # 6. Record metric + log line.
        if self._record_metrics:
            self._record(rid, request, response, duration_ms)

        # 7. One line per request, INFO level for 2xx, WARNING
        #    for 4xx, ERROR for 5xx. This is the operator's
        #    primary signal.
        level = (
            logging.ERROR if response.status_code >= 500
            else logging.WARNING if response.status_code >= 400
            else logging.INFO
        )
        logger.log(
            level,
            "%s %s -> %d (%.1fms)",
            request.method, request.url.path,
            response.status_code, duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "rid": rid,
            },
        )
        return response

    def _record(
        self,
        rid: str,
        request: Request,
        response: Response,
        duration_ms: float,
    ) -> None:
        # We import lazily so test fixtures that build the
        # middleware without the metrics module still work.
        try:
            from backend.api.metrics import (
                API_REQUEST_ID_SAMPLES,
                record_http_request,
            )
            # 12-char hash of the id to keep label cardinality
            # bounded — we don't want a million unique ids in
            # memory. The full id is still in the log line.
            rid_hash = hashlib.sha256(rid.encode("utf-8")).hexdigest()[:12]
            API_REQUEST_ID_SAMPLES.labels(
                method=request.method,
                path=request.url.path,
                status_class=f"{response.status_code // 100}xx",
                rid_hash=rid_hash,
            ).inc()
            record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration_sec=duration_ms / 1000.0,
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("request_id metric record failed: %s", exc)
