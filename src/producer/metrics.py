"""
Producer custom Prometheus metrics.

Provides observability for the LMView exchange producer:
  - Ticker dedup state (in-memory, survives via Redis snapshot)
  - Failover state transitions (Kafka <-> direct Redis)
  - Per-exchange per-symbol throughput
  - Health monitor state (Kafka + Flink reachability)
  - Direct Redis write path (when Kafka bypass active)

These metrics complement the basic counters already declared in
``src/producer/main.py`` and are intended to be imported from there
plus ``src/producer/health_monitor.py``.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram

# ─────────────────────────────────────────────────────────────────────────────
# Dedup state (in-memory ticker throttle)
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: number of distinct symbols currently tracked in dedup state
DEDUP_STATE_SIZE = Gauge(
    "producer_dedup_state_size",
    "Number of symbols currently in the per-symbol dedup dictionary",
)

# Counter: ticker messages skipped by the price-changed / heartbeat gate
DEDUP_DUPLICATES_SKIPPED = Counter(
    "producer_dedup_duplicates_skipped_total",
    "Ticker messages skipped because price did not change and heartbeat not due",
    ["exchange"],
)

# Counter: ticker messages actually forwarded downstream
DEDUP_MESSAGES_FORWARDED = Counter(
    "producer_dedup_messages_forwarded_total",
    "Ticker messages forwarded to Kafka / direct Redis after dedup check",
    ["exchange", "destination"],  # destination: kafka | direct_redis
)

# Gauge: last seen dedup decision timestamp (monotonic) per exchange
DEDUP_LAST_DECISION = Gauge(
    "producer_dedup_last_decision_timestamp_seconds",
    "Unix timestamp of the most recent dedup decision",
    ["exchange"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Failover state (health-gated Kafka <-> Direct Redis)
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: 1 if the producer is currently bypassing Kafka and writing direct to Redis
DIRECT_REDIS_ACTIVE = Gauge(
    "producer_direct_redis_active",
    "1 if the producer is currently writing directly to Redis (Kafka bypass)",
)

# Counter: number of times the failover state has changed
FAILOVER_TRANSITIONS = Counter(
    "producer_failover_transitions_total",
    "Number of failover state transitions",
    ["from_state", "to_state"],  # from_state/to_state: kafka | direct_redis
)

# Histogram: time spent in the direct-Redis (degraded) mode
FAILOVER_DURATION = Histogram(
    "producer_failover_duration_seconds",
    "Time the producer spent in the direct-Redis (bypass) mode",
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600, float("inf")),
)

# Counter: direct-Redis write attempts and failures
DIRECT_REDIS_WRITES = Counter(
    "producer_direct_redis_writes_total",
    "Direct Redis writes performed while bypassing Kafka",
    ["exchange", "key_pattern"],  # key_pattern: trade_latest | ticker_latest | depth | candle
)

DIRECT_REDIS_FAILURES = Counter(
    "producer_direct_redis_failures_total",
    "Direct Redis write failures",
    ["exchange", "key_pattern", "reason"],
)

# Histogram: direct-Redis write latency
DIRECT_REDIS_WRITE_LATENCY = Histogram(
    "producer_direct_redis_write_latency_seconds",
    "Direct Redis write latency",
    ["exchange", "key_pattern"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float("inf")),
)


# ─────────────────────────────────────────────────────────────────────────────
# Health monitor (Kafka + Flink reachability)
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: 1 if Kafka is reachable and the producer considers it healthy
KAFKA_HEALTHY = Gauge(
    "producer_kafka_healthy",
    "1 if the producer's most recent Kafka health check succeeded",
)

# Gauge: 1 if Flink JobManager is reachable
FLINK_HEALTHY = Gauge(
    "producer_flink_healthy",
    "1 if the producer's most recent Flink JobManager health check succeeded",
)

# Histogram: round-trip time for the Kafka health probe
KAFKA_PROBE_DURATION = Histogram(
    "producer_kafka_probe_duration_seconds",
    "Kafka health probe latency",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, float("inf")),
)

# Histogram: round-trip time for the Flink health probe
FLINK_PROBE_DURATION = Histogram(
    "producer_flink_probe_duration_seconds",
    "Flink health probe latency",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, float("inf")),
)

# Counter: cumulative Kafka probe failures
KAFKA_PROBE_FAILURES = Counter(
    "producer_kafka_probe_failures_total",
    "Kafka health probe failures",
    ["reason"],
)

# Counter: cumulative Flink probe failures
FLINK_PROBE_FAILURES = Counter(
    "producer_flink_probe_failures_total",
    "Flink health probe failures",
    ["reason"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Exchange WebSocket lifecycle
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: timestamp of the last successful message per exchange + stream
EXCHANGE_LAST_MESSAGE = Gauge(
    "producer_exchange_last_message_timestamp_seconds",
    "Unix timestamp of the last message received from the exchange",
    ["exchange", "stream"],  # stream: ticker | trade | kline | depth
)

# Counter: per-symbol messages received from the exchange (before dedup)
EXCHANGE_MESSAGES_RECEIVED = Counter(
    "producer_exchange_messages_received_total",
    "Messages received from the exchange WebSocket",
    ["exchange", "stream"],
)

# Gauge: connected status per exchange stream
EXCHANGE_WS_CONNECTED = Gauge(
    "producer_exchange_ws_connected",
    "1 if the WebSocket for an exchange+stream is currently connected",
    ["exchange", "stream"],
)

# Counter: cumulative backoff sleep time (rough) for reconnect storms
RECONNECT_BACKOFF_SECONDS = Counter(
    "producer_reconnect_backoff_seconds_total",
    "Cumulative backoff sleep time in seconds (reconnect storms)",
    ["exchange", "stream"],
)

# Gauge: timestamp of the last heartbeat per thread (producer-level
# liveness, complements the exchange-stream ``EXCHANGE_LAST_MESSAGE``
# gauge). Different threads (binance-ticker, okx-ticker, okx-trade,
# health-monitor, etc.) each set their own row.
HEARTBEAT_TIMESTAMP = Gauge(
    "producer_heartbeat_timestamp_seconds",
    "Unix timestamp of last heartbeat per thread",
    ["thread"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def init_metrics() -> None:
    """Initialize gauges with safe defaults at producer boot."""
    DIRECT_REDIS_ACTIVE.set(0)
    KAFKA_HEALTHY.set(1)
    FLINK_HEALTHY.set(1)
    DEDUP_STATE_SIZE.set(0)


def record_kafka_probe(success: bool, duration_sec: float, reason: Optional[str] = None) -> None:
    """Update Kafka health probe metrics."""
    KAFKA_HEALTHY.set(1 if success else 0)
    KAFKA_PROBE_DURATION.observe(duration_sec)
    if not success and reason:
        KAFKA_PROBE_FAILURES.labels(reason=reason).inc()


def record_flink_probe(success: bool, duration_sec: float, reason: Optional[str] = None) -> None:
    """Update Flink health probe metrics."""
    FLINK_HEALTHY.set(1 if success else 0)
    FLINK_PROBE_DURATION.observe(duration_sec)
    if not success and reason:
        FLINK_PROBE_FAILURES.labels(reason=reason).inc()


def record_dedup_decision(
    exchange: str,
    skipped: int,
    forwarded: int,
    destination: str,
) -> None:
    """Update dedup counters for a ticker batch."""
    if skipped:
        DEDUP_DUPLICATES_SKIPPED.labels(exchange=exchange).inc(skipped)
    if forwarded:
        DEDUP_MESSAGES_FORWARDED.labels(exchange=exchange, destination=destination).inc(forwarded)
    DEDUP_LAST_DECISION.labels(exchange=exchange).set(time.time())


def record_failover_transition(from_state: str, to_state: str) -> None:
    """Record a failover state transition and toggle the active gauge."""
    FAILOVER_TRANSITIONS.labels(from_state=from_state, to_state=to_state).inc()
    DIRECT_REDIS_ACTIVE.set(1 if to_state == "direct_redis" else 0)


def record_direct_redis_write(
    exchange: str,
    key_pattern: str,
    duration_sec: float,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """Record a direct-Redis write attempt."""
    DIRECT_REDIS_WRITE_LATENCY.labels(exchange=exchange, key_pattern=key_pattern).observe(duration_sec)
    if success:
        DIRECT_REDIS_WRITES.labels(exchange=exchange, key_pattern=key_pattern).inc()
    else:
        DIRECT_REDIS_FAILURES.labels(
            exchange=exchange, key_pattern=key_pattern, reason=error or "unknown"
        ).inc()


def record_exchange_message(exchange: str, stream: str, n: int = 1) -> None:
    """Record a batch of messages received from an exchange WebSocket."""
    EXCHANGE_MESSAGES_RECEIVED.labels(exchange=exchange, stream=stream).inc(n)
    EXCHANGE_LAST_MESSAGE.labels(exchange=exchange, stream=stream).set(time.time())


def record_exchange_ws_state(exchange: str, stream: str, connected: bool) -> None:
    """Update WebSocket connection state for an exchange+stream pair."""
    EXCHANGE_WS_CONNECTED.labels(exchange=exchange, stream=stream).set(1 if connected else 0)


def record_reconnect_backoff(exchange: str, stream: str, sleep_sec: float) -> None:
    """Record cumulative backoff time for a reconnect attempt."""
    RECONNECT_BACKOFF_SECONDS.labels(exchange=exchange, stream=stream).inc(sleep_sec)


__all__ = [
    # dedup
    "DEDUP_STATE_SIZE",
    "DEDUP_DUPLICATES_SKIPPED",
    "DEDUP_MESSAGES_FORWARDED",
    "DEDUP_LAST_DECISION",
    # failover
    "DIRECT_REDIS_ACTIVE",
    "FAILOVER_TRANSITIONS",
    "FAILOVER_DURATION",
    "DIRECT_REDIS_WRITES",
    "DIRECT_REDIS_FAILURES",
    "DIRECT_REDIS_WRITE_LATENCY",
    # health
    "KAFKA_HEALTHY",
    "FLINK_HEALTHY",
    "KAFKA_PROBE_DURATION",
    "FLINK_PROBE_DURATION",
    "KAFKA_PROBE_FAILURES",
    "FLINK_PROBE_FAILURES",
    # exchange
    "EXCHANGE_LAST_MESSAGE",
    "EXCHANGE_MESSAGES_RECEIVED",
    "EXCHANGE_WS_CONNECTED",
    "RECONNECT_BACKOFF_SECONDS",
    # heartbeat
    "HEARTBEAT_TIMESTAMP",
    # helpers
    "init_metrics",
    "record_kafka_probe",
    "record_flink_probe",
    "record_dedup_decision",
    "record_failover_transition",
    "record_direct_redis_write",
    "record_exchange_message",
    "record_exchange_ws_state",
    "record_reconnect_backoff",
]
