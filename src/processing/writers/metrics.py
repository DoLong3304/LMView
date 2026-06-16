"""
Flink writer custom Prometheus metrics.

Provides observability for the LMView Flink processing pipeline:
  - Per-writer flush latency and throughput
  - Per-writer buffer size and records per flush
  - Indicator state warmup duration (post-restart hydration)
  - Checkpoint outcomes (size, duration, failures)
  - Kafka source emit rate
  - Multi-sink fan-out (key -> N sinks)

These metrics are exposed on the Flink JobManager / TaskManager
Prometheus reporter (default ports 9249) and aggregated centrally.
Writers (``KeyDBWriter``, ``KeyDBKlineWriter``, etc.) should import
the helpers below to update metrics at every flush / state change.
"""

from __future__ import annotations

import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram


# ─────────────────────────────────────────────────────────────────────────────
# Writer-level throughput and latency
# ─────────────────────────────────────────────────────────────────────────────

# Histogram: time taken to flush a writer's buffer to its sink
WRITER_FLUSH_DURATION = Histogram(
    "flink_writer_flush_duration_seconds",
    "Flink writer flush duration",
    ["writer", "sink"],  # writer: ticker | kline | kline_agg | depth | trade | indicator | influx_ticker | influx_kline
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, float("inf")),
)

# Gauge: number of records currently buffered in a writer
WRITER_BUFFER_SIZE = Gauge(
    "flink_writer_buffer_size",
    "Number of records currently buffered in a writer (between flushes)",
    ["writer", "sink"],
)

# Histogram: number of records flushed per flush call
WRITER_RECORDS_PER_FLUSH = Histogram(
    "flink_writer_records_per_flush",
    "Number of records flushed per flush call",
    ["writer", "sink"],
    buckets=(1, 10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, float("inf")),
)

# Counter: total records emitted by a writer to its sink
WRITER_RECORDS_EMITTED = Counter(
    "flink_writer_records_emitted_total",
    "Total records emitted by a writer to its sink",
    ["writer", "sink"],
)

# Counter: total flushes performed by a writer
WRITER_FLUSH_CALLS = Counter(
    "flink_writer_flush_calls_total",
    "Total flush calls by a writer",
    ["writer", "sink", "trigger"],  # trigger: time | size | close | checkpoint
)

# Counter: per-sink write errors
WRITER_ERRORS = Counter(
    "flink_writer_errors_total",
    "Errors encountered by a writer while flushing",
    ["writer", "sink", "error_type"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Indicator / aggregator state
# ─────────────────────────────────────────────────────────────────────────────

# Histogram: time to warm up the indicator / EMA state after a restart
INDICATOR_STATE_WARMUP_DURATION = Histogram(
    "flink_indicator_state_warmup_duration_seconds",
    "Time taken to warm up indicator state after a Flink restart",
    ["state_type"],  # state_type: ema | rsi | bb | macd | candle_deque
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, float("inf")),
)

# Gauge: number of state keys (per symbol) currently in memory
INDICATOR_STATE_KEYS = Gauge(
    "flink_indicator_state_keys",
    "Number of distinct state keys currently held in writer memory",
    ["state_type"],
)

# Counter: indicator recomputations triggered by an event
INDICATOR_RECOMPUTATIONS = Counter(
    "flink_indicator_recomputations_total",
    "Indicator recomputations triggered",
    ["indicator", "trigger"],  # trigger: new_candle | gap_fill | late_event
)

# Counter: candle gap-fill operations (forward-fill from previous close)
KLINE_GAP_FILLS = Counter(
    "flink_kline_gap_fills_total",
    "1-second candle gap-fill operations (forward-fill from previous close)",
    ["exchange", "symbol"],
)

# Gauge: current kline aggregator window fill ratio (0-1)
KLINE_WINDOW_FILL_RATIO = Gauge(
    "flink_kline_window_fill_ratio",
    "Current 1-minute kline aggregator window fill ratio (0-1)",
    ["exchange", "symbol"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint observability
# ─────────────────────────────────────────────────────────────────────────────

# Histogram: checkpoint duration
FLINK_CHECKPOINT_DURATION = Histogram(
    "flink_checkpoint_duration_seconds",
    "Flink checkpoint duration",
    ["job", "result"],  # result: success | failure
    buckets=(0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float("inf")),
)

# Gauge: most recent checkpoint size
FLINK_CHECKPOINT_SIZE = Gauge(
    "flink_checkpoint_size_bytes",
    "Most recent checkpoint size in bytes",
    ["job"],
)

# Counter: cumulative checkpoint failures
FLINK_CHECKPOINT_FAILURES = Counter(
    "flink_checkpoint_failures_total",
    "Cumulative checkpoint failures",
    ["job", "reason"],
)

# Counter: cumulative successful checkpoints
FLINK_CHECKPOINT_SUCCESS = Counter(
    "flink_checkpoint_success_total",
    "Cumulative successful checkpoints",
    ["job"],
)

# Gauge: checkpoint alignment buffer bytes (unaligned checkpoints only)
FLINK_CHECKPOINT_ALIGNMENT_BYTES = Gauge(
    "flink_checkpoint_alignment_bytes",
    "Checkpoint alignment buffer size in bytes (unaligned checkpoints)",
    ["job", "subtask"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Kafka source consumption
# ─────────────────────────────────────────────────────────────────────────────

# Counter: records consumed from Kafka per topic / partition
KAFKA_SOURCE_RECORDS_IN = Counter(
    "flink_kafka_source_records_in_total",
    "Records consumed from Kafka by the Flink source",
    ["topic", "partition"],
)

# Counter: records dropped (after consumer-side filtering or late event)
KAFKA_SOURCE_RECORDS_DROPPED = Counter(
    "flink_kafka_source_records_dropped_total",
    "Records dropped after Kafka consumption (deserialization, schema, late)",
    ["topic", "reason"],
)

# Gauge: current Kafka source watermark lag (event_time vs wallclock)
KAFKA_SOURCE_WATERMARK_LAG = Gauge(
    "flink_kafka_source_watermark_lag_seconds",
    "Watermark lag in seconds (event_time vs current time)",
    ["topic"],
)

# Histogram: time to deserialise one Kafka record
KAFKA_SOURCE_DESERIALIZE_DURATION = Histogram(
    "flink_kafka_source_deserialize_duration_seconds",
    "Kafka record deserialisation duration",
    ["topic"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, float("inf")),
)


# ─────────────────────────────────────────────────────────────────────────────
# Per-key (symbol) observability
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: last seen event_time per (exchange, symbol) key
WRITER_LAST_EVENT_TIME = Gauge(
    "flink_writer_last_event_timestamp_seconds",
    "Unix timestamp of the most recent event for a key",
    ["writer", "exchange", "symbol"],
)

# Counter: distinct keys ever seen by a writer
WRITER_KEYS_TOTAL = Counter(
    "flink_writer_keys_total",
    "Distinct keys seen by a writer since startup",
    ["writer", "exchange"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Backpressure and operator health
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: backpressure time per second (ms/s) per subtask
FLINK_OPERATOR_BACKPRESSURE = Gauge(
    "flink_operator_backpressure_ms_per_second",
    "Backpressure time per second (ms/s) per Flink operator subtask",
    ["job", "subtask", "operator"],
)

# Gauge: per-operator in-flight record count
FLINK_OPERATOR_INFLIGHT = Gauge(
    "flink_operator_inflight_records",
    "Number of records currently in-flight in an operator",
    ["job", "subtask", "operator"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle helpers
# ─────────────────────────────────────────────────────────────────────────────

# Track which writer identities we have already seen so we only seed
# the per-writer gauges once. Avoids "no data" dashboards when the
# first event for a writer hasn't arrived yet.
_INITIALISED_WRITERS: set[str] = set()
_INITIALISED_SINKS: set[tuple[str, str]] = set()


def init_metrics() -> None:
    """Seed writer / sink gauges with 0 so dashboards show data immediately.

    Safe to call multiple times — subsequent calls are no-ops. Should
    be called from each writer's ``open()`` method (or once at
    pipeline boot from ``pipeline.py``) so that the very first scrape
    by Prometheus sees meaningful 0-valued gauges instead of "no data".
    """
    for writer in ("keydb_ticker", "keydb_kline", "keydb_trade", "keydb_depth",
                   "influxdb_ticker", "influxdb_kline", "indicator",
                   "kline_aggregator"):
        if writer in _INITIALISED_WRITERS:
            continue
        for sink in ("redis", "influxdb"):
            key = (writer, sink)
            if key not in _INITIALISED_SINKS:
                WRITER_BUFFER_SIZE.labels(writer=writer, sink=sink).set(0)
                _INITIALISED_SINKS.add(key)
        _INITIALISED_WRITERS.add(writer)

    # Pre-create the indicator state gauges
    for state_type in ("ema", "rsi", "bb", "macd", "macd_signal",
                       "candle_deque", "closes_deque", "volumes_deque"):
        INDICATOR_STATE_KEYS.labels(state_type=state_type).set(0)


def record_flush(
    writer: str,
    sink: str,
    duration_sec: float,
    n_records: int,
    trigger: str = "time",
    error: Optional[str] = None,
) -> None:
    """Record a single writer flush outcome."""
    WRITER_FLUSH_DURATION.labels(writer=writer, sink=sink).observe(duration_sec)
    WRITER_RECORDS_PER_FLUSH.labels(writer=writer, sink=sink).observe(n_records)
    WRITER_RECORDS_EMITTED.labels(writer=writer, sink=sink).inc(n_records)
    WRITER_FLUSH_CALLS.labels(writer=writer, sink=sink, trigger=trigger).inc()
    if error:
        WRITER_ERRORS.labels(writer=writer, sink=sink, error_type=error).inc()


def record_buffer_size(writer: str, sink: str, size: int) -> None:
    """Update the current buffer size of a writer."""
    WRITER_BUFFER_SIZE.labels(writer=writer, sink=sink).set(size)


def record_indicator_warmup(state_type: str, duration_sec: float) -> None:
    """Record indicator state warmup duration after a Flink restart."""
    INDICATOR_STATE_WARMUP_DURATION.labels(state_type=state_type).observe(duration_sec)


def record_indicator_recompute(indicator: str, trigger: str = "new_candle") -> None:
    """Record a single indicator recomputation."""
    INDICATOR_RECOMPUTATIONS.labels(indicator=indicator, trigger=trigger).inc()


def record_kline_gap_fill(exchange: str, symbol: str) -> None:
    """Record a 1-second candle gap-fill operation."""
    KLINE_GAP_FILLS.labels(exchange=exchange, symbol=symbol).inc()


def record_kline_window_fill_ratio(exchange: str, symbol: str, ratio: float) -> None:
    """Update the 1-minute kline aggregator window fill ratio (0-1)."""
    KLINE_WINDOW_FILL_RATIO.labels(exchange=exchange, symbol=symbol).set(ratio)


def record_checkpoint(
    job: str,
    duration_sec: float,
    size_bytes: int,
    success: bool,
    reason: Optional[str] = None,
) -> None:
    """Record a checkpoint outcome (success or failure)."""
    result = "success" if success else "failure"
    FLINK_CHECKPOINT_DURATION.labels(job=job, result=result).observe(duration_sec)
    if success:
        FLINK_CHECKPOINT_SUCCESS.labels(job=job).inc()
        FLINK_CHECKPOINT_SIZE.labels(job=job).set(size_bytes)
    else:
        FLINK_CHECKPOINT_FAILURES.labels(job=job, reason=reason or "unknown").inc()


def record_kafka_source(topic: str, partition: int, n: int = 1) -> None:
    """Record N records consumed from a Kafka topic/partition."""
    KAFKA_SOURCE_RECORDS_IN.labels(topic=topic, partition=str(partition)).inc(n)


def record_kafka_source_drop(topic: str, reason: str) -> None:
    """Record a Kafka record that was dropped after consumption."""
    KAFKA_SOURCE_RECORDS_DROPPED.labels(topic=topic, reason=reason).inc()


def record_kafka_source_watermark(topic: str, lag_sec: float) -> None:
    """Update the watermark lag gauge for a Kafka topic."""
    KAFKA_SOURCE_WATERMARK_LAG.labels(topic=topic).set(lag_sec)


def record_kafka_source_deserialize(topic: str, duration_sec: float) -> None:
    """Record Kafka record deserialisation latency."""
    KAFKA_SOURCE_DESERIALIZE_DURATION.labels(topic=topic).observe(duration_sec)


def record_writer_event_time(writer: str, exchange: str, symbol: str, event_ts: float) -> None:
    """Update the last seen event_time for a (writer, exchange, symbol) key."""
    WRITER_LAST_EVENT_TIME.labels(writer=writer, exchange=exchange, symbol=symbol).set(event_ts)


def record_writer_new_key(writer: str, exchange: str) -> None:
    """Record that a writer has seen a new key for the first time."""
    WRITER_KEYS_TOTAL.labels(writer=writer, exchange=exchange).inc()


def record_backpressure(job: str, subtask: str, operator: str, ms_per_sec: float) -> None:
    """Update per-subtask backpressure gauge."""
    FLINK_OPERATOR_BACKPRESSURE.labels(job=job, subtask=subtask, operator=operator).set(ms_per_sec)


def record_inflight(job: str, subtask: str, operator: str, count: int) -> None:
    """Update per-subtask in-flight record count gauge."""
    FLINK_OPERATOR_INFLIGHT.labels(job=job, subtask=subtask, operator=operator).set(count)


# ─────────────────────────────────────────────────────────────────────────────
# Whale alert metrics (Task 2, v0.24.4)
# ─────────────────────────────────────────────────────────────────────────────

# Counter: whale alerts detected (filtered from crypto_trades)
WHALE_ALERTS_DETECTED = Counter(
    "flink_whale_alerts_detected_total",
    "Whale alerts detected (single trade notional >= threshold)",
    ["exchange", "symbol", "side"],  # side: buy | sell
)

# Histogram: distribution of notional USD values for whale alerts
WHALE_ALERT_NOTIONAL = Histogram(
    "flink_whale_alert_notional_usd",
    "Notional USD value of detected whale alerts",
    ["exchange", "side"],
    buckets=(100_000, 250_000, 500_000, 1_000_000, 2_500_000, 5_000_000,
             10_000_000, 25_000_000, 50_000_000, 100_000_000, float("inf")),
)

# Gauge: rolling count of whale alerts in last 5 min (per symbol)
WHALE_ALERT_RECENT_COUNT = Gauge(
    "flink_whale_alert_recent_count",
    "Whale alerts in last 5 min, per symbol",
    ["exchange", "symbol"],
)


def record_whale_alert(
    exchange: str, symbol: str, side: str, notional_usd: float,
) -> None:
    """Record a detected whale alert.

    Increments WHALE_ALERTS_DETECTED counter and updates the notional
    histogram. The recent-count gauge is best updated by a sidecar
    scraper (1-min interval) since Flink state for rolling counts is
    non-trivial; we leave that hook in place but don't populate it
    inline to keep the hot path lean.
    """
    WHALE_ALERTS_DETECTED.labels(
        exchange=exchange, symbol=symbol, side=side,
    ).inc()
    WHALE_ALERT_NOTIONAL.labels(
        exchange=exchange, side=side,
    ).observe(notional_usd)


__all__ = [
    # writer
    "WRITER_FLUSH_DURATION",
    "WRITER_BUFFER_SIZE",
    "WRITER_RECORDS_PER_FLUSH",
    "WRITER_RECORDS_EMITTED",
    "WRITER_FLUSH_CALLS",
    "WRITER_ERRORS",
    # indicator / state
    "INDICATOR_STATE_WARMUP_DURATION",
    "INDICATOR_STATE_KEYS",
    "INDICATOR_RECOMPUTATIONS",
    "KLINE_GAP_FILLS",
    "KLINE_WINDOW_FILL_RATIO",
    # checkpoint
    "FLINK_CHECKPOINT_DURATION",
    "FLINK_CHECKPOINT_SIZE",
    "FLINK_CHECKPOINT_FAILURES",
    "FLINK_CHECKPOINT_SUCCESS",
    "FLINK_CHECKPOINT_ALIGNMENT_BYTES",
    # kafka source
    "KAFKA_SOURCE_RECORDS_IN",
    "KAFKA_SOURCE_RECORDS_DROPPED",
    "KAFKA_SOURCE_WATERMARK_LAG",
    "KAFKA_SOURCE_DESERIALIZE_DURATION",
    # per-key
    "WRITER_LAST_EVENT_TIME",
    "WRITER_KEYS_TOTAL",
    # backpressure
    "FLINK_OPERATOR_BACKPRESSURE",
    "FLINK_OPERATOR_INFLIGHT",
    # whale alerts (Task 2)
    "WHALE_ALERTS_DETECTED",
    "WHALE_ALERT_NOTIONAL",
    "WHALE_ALERT_RECENT_COUNT",
    # helpers
    "init_metrics",
    "record_flush",
    "record_buffer_size",
    "record_indicator_warmup",
    "record_indicator_recompute",
    "record_kline_gap_fill",
    "record_kline_window_fill_ratio",
    "record_checkpoint",
    "record_kafka_source",
    "record_kafka_source_drop",
    "record_kafka_source_watermark",
    "record_kafka_source_deserialize",
    "record_writer_event_time",
    "record_writer_new_key",
    "record_backpressure",
    "record_inflight",
    "record_whale_alert",
]
