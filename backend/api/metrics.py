"""
Backend (FastAPI) custom Prometheus metrics.

Provides observability for the LMView serving layer:
  - HTTP request latency + error rate per endpoint
  - WebSocket connection lifecycle (connect / disconnect / errors)
  - WebSocket message push throughput + latency + size
  - Multi-source fallback chain (Redis -> InfluxDB -> Trino -> REST)
  - Per-symbol data freshness tracking
  - Per-source hit / miss / stale-data rates

These metrics are exposed on the standard ``/metrics`` endpoint via
``prometheus-fastapi-instrumentator`` (already wired in ``backend/app.py``)
by simply importing this module — no extra configuration required.
"""

from __future__ import annotations

import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram


# ─────────────────────────────────────────────────────────────────────────────
# HTTP request observability (per-endpoint)
# ─────────────────────────────────────────────────────────────────────────────

# Histogram: latency for every request, labelled by method + route + status
HTTP_REQUEST_DURATION = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)

# Counter: total HTTP requests per endpoint
HTTP_REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

# Counter: HTTP error responses (4xx + 5xx) for faster alerting
HTTP_ERRORS_TOTAL = Counter(
    "api_errors_total",
    "Total HTTP error responses (4xx/5xx)",
    ["method", "endpoint", "status"],
)

# Counter: in-flight HTTP requests (for capacity planning)
HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "api_requests_in_flight",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket connection observability
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: number of currently active WebSocket connections per route
WS_CONNECTIONS_ACTIVE = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
    ["route"],
)

# Counter: cumulative WebSocket connection attempts
WS_CONNECTION_ATTEMPTS = Counter(
    "websocket_connection_attempts_total",
    "WebSocket connection attempts",
    ["route", "result"],  # result: accepted | rejected
)

# Counter: WebSocket connection errors (handshake, upgrade, post-upgrade)
WS_CONNECTION_ERRORS = Counter(
    "websocket_connection_errors_total",
    "WebSocket connection errors",
    ["route", "error_type"],  # error_type: handshake | upgrade | runtime
)

# Counter: WebSocket disconnections
WS_DISCONNECTS = Counter(
    "websocket_disconnects_total",
    "WebSocket disconnections",
    ["route", "reason"],  # reason: client_close | server_close | timeout | error
)

# Histogram: WebSocket connection lifetime
WS_CONNECTION_LIFETIME = Histogram(
    "websocket_connection_lifetime_seconds",
    "WebSocket connection lifetime in seconds",
    ["route"],
    buckets=(1, 10, 30, 60, 300, 600, 1800, 3600, float("inf")),
)


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket message serving
# ─────────────────────────────────────────────────────────────────────────────

# Counter: WebSocket messages pushed to clients
WS_MESSAGES_PUSHED = Counter(
    "websocket_messages_pushed_total",
    "WebSocket messages pushed to clients",
    ["route", "data_type"],  # data_type: ticker | candle | trade | orderbook | indicator
)

# Counter: WebSocket messages dropped (slow client, buffer overflow, etc.)
WS_MESSAGES_DROPPED = Counter(
    "websocket_messages_dropped_total",
    "WebSocket messages dropped before reaching a client",
    ["route", "reason"],
)

# Histogram: size of WebSocket messages in bytes
WS_MESSAGE_SIZE = Histogram(
    "websocket_message_size_bytes",
    "WebSocket message size in bytes",
    ["route", "data_type"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000, float("inf")),
)

# Histogram: time spent serialising + sending one WebSocket frame
WS_MESSAGE_PUSH_DURATION = Histogram(
    "websocket_message_push_duration_seconds",
    "Time to push a single WebSocket message",
    ["route"],
    buckets=(0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float("inf")),
)

# Gauge: in-memory message buffer size per client (slow-client detection)
WS_CLIENT_BUFFER_SIZE = Gauge(
    "websocket_client_buffer_size",
    "Buffered messages per slow client (last sample)",
    ["route", "client_id"],
)

# Histogram: time between two consecutive push cycles in the WS loop
WS_LOOP_CYCLE_DURATION = Histogram(
    "websocket_loop_cycle_duration_seconds",
    "Time between two consecutive WebSocket polling cycles",
    ["route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, float("inf")),
)

# Counter: change-detection outcomes (no data updated, push skipped)
WS_NOOP_PUSHES = Counter(
    "websocket_noop_pushes_total",
    "WebSocket cycles where nothing changed (push skipped)",
    ["route", "data_type"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Multi-source fallback chain (Redis -> InfluxDB -> Trino -> REST)
# ─────────────────────────────────────────────────────────────────────────────

# Counter: lookups against each data source
SOURCE_LOOKUPS = Counter(
    "multi_source_lookups_total",
    "Multi-source data lookups",
    ["source", "data_type", "result"],  # source: redis | influxdb | trino | rest
)

# Histogram: lookup latency per source
SOURCE_LOOKUP_DURATION = Histogram(
    "source_lookup_duration_seconds",
    "Multi-source lookup latency",
    ["source", "data_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf")),
)

# Counter: source unavailable events (network error, timeout, etc.)
SOURCE_UNAVAILABLE = Counter(
    "source_unavailable_total",
    "Source unavailability events (network error / timeout)",
    ["source", "data_type", "reason"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Trino query pool (B11 — blocking thread pool, asyncio.to_thread)
# ─────────────────────────────────────────────────────────────────────────────

# Histogram: Trino query duration (regardless of success/failure)
TRINO_QUERY_DURATION = Histogram(
    "backend_trino_query_duration_seconds",
    "Trino query wall-clock duration (incl. asyncio.to_thread overhead)",
    ["query_type", "result"],  # result: success | failure
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)

# Counter: Trino query failures
TRINO_QUERY_FAILURES = Counter(
    "backend_trino_query_failures_total",
    "Trino query failures",
    ["query_type", "reason"],
)

# Gauge: in-flight Trino queries (active thread-pool tasks)
TRINO_ACTIVE_QUERIES = Gauge(
    "backend_trino_active_queries",
    "Number of in-flight Trino queries (asyncio.to_thread tasks)",
)

# Gauge: trino fallback events (caller decided to use Redis/ticker)
TRINO_FALLBACK = Counter(
    "backend_trino_fallback_total",
    "Endpoint fell back from Trino to Redis/ticker",
    ["endpoint", "reason"],
)

# Counter: stale-data incidents (data too old for use)
SOURCE_STALE_DATA = Counter(
    "source_stale_data_total",
    "Stale-data incidents per source (data older than freshness threshold)",
    ["source", "data_type"],
)

# Counter: multi-source lookup chain terminations
SOURCE_CHAIN_OUTCOME = Counter(
    "multi_source_chain_outcome_total",
    "Multi-source lookup chain terminations",
    ["data_type", "terminating_source"],  # which source finally served the request
)

# Gauge: per-symbol last-update timestamp per source
SOURCE_LAST_UPDATE = Gauge(
    "source_last_update_timestamp_seconds",
    "Unix timestamp of the most recent data point for a symbol",
    ["source", "exchange", "symbol"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Cache observability (in-process FastAPI response cache)
# ─────────────────────────────────────────────────────────────────────────────

# Counter: cache hits and misses
CACHE_OPS = Counter(
    "api_cache_ops_total",
    "In-process API cache operations",
    ["endpoint", "result"],  # result: hit | miss | bypass
)

# Histogram: cache entry age when served
CACHE_AGE = Histogram(
    "api_cache_entry_age_seconds",
    "Age of the cache entry when served",
    ["endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 60.0, float("inf")),
)

# Gauge: current cache size in entries
CACHE_SIZE = Gauge(
    "api_cache_size_entries",
    "Current number of entries in the in-process API cache",
    ["endpoint"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def record_http_request(
    method: str,
    endpoint: str,
    status: int,
    duration_sec: float,
) -> None:
    """Update HTTP-level metrics for a completed request."""
    status_str = str(status)
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint, status=status_str).observe(duration_sec)
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status_str).inc()
    if status >= 400:
        HTTP_ERRORS_TOTAL.labels(method=method, endpoint=endpoint, status=status_str).inc()


def record_ws_connection(route: str, accepted: bool) -> None:
    """Record a WebSocket connection attempt outcome."""
    result = "accepted" if accepted else "rejected"
    WS_CONNECTION_ATTEMPTS.labels(route=route, result=result).inc()
    if accepted:
        WS_CONNECTIONS_ACTIVE.labels(route=route).inc()


def record_ws_disconnect(route: str, reason: str, lifetime_sec: float) -> None:
    """Record a WebSocket disconnection and connection lifetime."""
    WS_DISCONNECTS.labels(route=route, reason=reason).inc()
    WS_CONNECTIONS_ACTIVE.labels(route=route).dec()
    WS_CONNECTION_LIFETIME.labels(route=route).observe(lifetime_sec)


def record_ws_connection_error(route: str, error_type: str) -> None:
    """Record a WebSocket connection error."""
    WS_CONNECTION_ERRORS.labels(route=route, error_type=error_type).inc()


def record_ws_message_push(
    route: str,
    data_type: str,
    size_bytes: int,
    duration_sec: float,
    dropped: bool = False,
    drop_reason: Optional[str] = None,
) -> None:
    """Record a WebSocket message push (success or drop)."""
    if dropped:
        WS_MESSAGES_DROPPED.labels(route=route, reason=drop_reason or "unknown").inc()
        return
    WS_MESSAGES_PUSHED.labels(route=route, data_type=data_type).inc()
    WS_MESSAGE_SIZE.labels(route=route, data_type=data_type).observe(size_bytes)
    WS_MESSAGE_PUSH_DURATION.labels(route=route).observe(duration_sec)


def record_ws_loop_cycle(route: str, duration_sec: float) -> None:
    """Record one full WebSocket polling cycle duration."""
    WS_LOOP_CYCLE_DURATION.labels(route=route).observe(duration_sec)


def record_ws_noop(route: str, data_type: str) -> None:
    """Record a WebSocket cycle where the data was unchanged."""
    WS_NOOP_PUSHES.labels(route=route, data_type=data_type).inc()


def record_source_lookup(
    source: str,
    data_type: str,
    duration_sec: float,
    success: bool = True,
    stale: bool = False,
    reason: Optional[str] = None,
) -> None:
    """Record a multi-source lookup outcome."""
    result = "success" if success and not stale else "stale" if stale else "error"
    SOURCE_LOOKUPS.labels(source=source, data_type=data_type, result=result).inc()
    SOURCE_LOOKUP_DURATION.labels(source=source, data_type=data_type).observe(duration_sec)
    if not success and reason:
        SOURCE_UNAVAILABLE.labels(source=source, data_type=data_type, reason=reason).inc()
    if stale:
        SOURCE_STALE_DATA.labels(source=source, data_type=data_type).inc()


def record_source_unavailable(source: str, data_type: str, reason: str) -> None:
    """Record a source-unavailability event (no duration, just count)."""
    SOURCE_UNAVAILABLE.labels(source=source, data_type=data_type, reason=reason).inc()


def record_source_chain_outcome(data_type: str, terminating_source: str) -> None:
    """Record which source finally served a multi-source lookup."""
    SOURCE_CHAIN_OUTCOME.labels(data_type=data_type, terminating_source=terminating_source).inc()


def record_source_freshness(source: str, exchange: str, symbol: str, ts: float) -> None:
    """Update per-symbol last-update timestamp gauge."""
    SOURCE_LAST_UPDATE.labels(source=source, exchange=exchange, symbol=symbol).set(ts)


def record_cache_op(endpoint: str, result: str, age_sec: Optional[float] = None) -> None:
    """Record an in-process cache operation."""
    CACHE_OPS.labels(endpoint=endpoint, result=result).inc()
    if age_sec is not None and result == "hit":
        CACHE_AGE.labels(endpoint=endpoint).observe(age_sec)


# ─────────────────────────────────────────────────────────────────────────────
# Frontend RUM (A9.1 — JS error rate)
# ─────────────────────────────────────────────────────────────────────────────

# Counter: JS error events caught by frontend/src/utils/rum.ts
FRONTEND_RUM_ERRORS = Counter(
    "frontend_rum_errors",
    "Frontend JS errors captured via RUM",
    ["type", "source"],  # type: error | perf | pageview
)

# Counter: pageview events
FRONTEND_RUM_PAGE_LOADS = Counter(
    "frontend_rum_page_loads",
    "Frontend page load events captured via RUM",
    ["route"],
)

# Histogram: Largest Contentful Paint (seconds)
FRONTEND_RUM_LCP = Histogram(
    "frontend_rum_lcp_seconds",
    "Frontend Largest Contentful Paint (seconds)",
    ["route"],
    buckets=(0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, float("inf")),
)

# Histogram: Interaction to Next Paint (seconds)
FRONTEND_RUM_INP = Histogram(
    "frontend_rum_inp_seconds",
    "Frontend Interaction to Next Paint (seconds)",
    ["route"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2.0, 4.0, float("inf")),
)


def record_frontend_rum_error(error_type: str, source: str = "browser") -> None:
    """Record a single frontend JS error caught by the RUM client."""
    FRONTEND_RUM_ERRORS.labels(type="error", source=source).inc()


def record_frontend_rum_pageview(route: str) -> None:
    """Record a frontend pageview event."""
    FRONTEND_RUM_PAGE_LOADS.labels(route=route).inc()


def record_frontend_rum_lcp(route: str, lcp_sec: float) -> None:
    """Observe a Largest Contentful Paint value (seconds)."""
    FRONTEND_RUM_LCP.labels(route=route).observe(lcp_sec)


def record_frontend_rum_inp(route: str, inp_sec: float) -> None:
    """Observe an Interaction to Next Paint value (seconds)."""
    FRONTEND_RUM_INP.labels(route=route).observe(inp_sec)


# ─────────────────────────────────────────────────────────────────────────────
# Rate limit (A10.2 — API rate limit hit)
# ─────────────────────────────────────────────────────────────────────────────

# Counter: 429 responses served by the in-process rate limiter
API_RATE_LIMITED_TOTAL = Counter(
    "api_rate_limited",
    "HTTP 429 responses served by the in-process rate limiter",
    ["ip_hash", "path"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Trino helpers (B11 — blocking thread pool)
# ─────────────────────────────────────────────────────────────────────────────

def record_trino_query(query_type: str, duration_sec: float, success: bool,
                       reason: str = "") -> None:
    """Record a Trino query outcome.

    ``query_type`` is a short label like "market_summary", "top_movers",
    "heatmap", etc. — used as a Prometheus label to slice latency.
    """
    result = "success" if success else "failure"
    TRINO_QUERY_DURATION.labels(query_type=query_type, result=result).observe(duration_sec)
    if not success:
        TRINO_QUERY_FAILURES.labels(query_type=query_type, reason=reason or "unknown").inc()


def record_trino_fallback(endpoint: str, reason: str) -> None:
    """Record that an endpoint fell back from Trino to Redis/ticker."""
    TRINO_FALLBACK.labels(endpoint=endpoint, reason=reason).inc()


__all__ = [
    # HTTP
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_ERRORS_TOTAL",
    "HTTP_REQUESTS_IN_FLIGHT",
    # WS connection
    "WS_CONNECTIONS_ACTIVE",
    "WS_CONNECTION_ATTEMPTS",
    "WS_CONNECTION_ERRORS",
    "WS_DISCONNECTS",
    "WS_CONNECTION_LIFETIME",
    # WS message
    "WS_MESSAGES_PUSHED",
    "WS_MESSAGES_DROPPED",
    "WS_MESSAGE_SIZE",
    "WS_MESSAGE_PUSH_DURATION",
    "WS_CLIENT_BUFFER_SIZE",
    "WS_LOOP_CYCLE_DURATION",
    "WS_NOOP_PUSHES",
    # multi-source
    "SOURCE_LOOKUPS",
    "SOURCE_LOOKUP_DURATION",
    "SOURCE_UNAVAILABLE",
    "SOURCE_STALE_DATA",
    "SOURCE_CHAIN_OUTCOME",
    "SOURCE_LAST_UPDATE",
    # trino (B11)
    "TRINO_QUERY_DURATION",
    "TRINO_QUERY_FAILURES",
    "TRINO_ACTIVE_QUERIES",
    "TRINO_FALLBACK",
    # cache
    "CACHE_OPS",
    "CACHE_AGE",
    "CACHE_SIZE",
    # helpers
    "record_http_request",
    "record_ws_connection",
    "record_ws_disconnect",
    "record_ws_connection_error",
    "record_ws_message_push",
    "record_ws_noop",
    "record_ws_loop_cycle",
    "record_source_lookup",
    "record_source_unavailable",
    "record_source_chain_outcome",
    "record_source_freshness",
    "record_cache_op",
    "record_trino_query",
    "record_trino_fallback",
]
