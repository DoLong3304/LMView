"""
AI / RAG custom Prometheus metrics.

Provides observability for the LMView AI Ask Mode pipeline:
  - Top-level request outcomes (allowed / blocked / fallback)
  - Scope gate decisions (in-scope / out-of-scope / injection)
  - Provider routing (per provider success / fallback / error)
  - RAG retrieval (duration, top-k, relevance score, cache hit/miss)
  - Embedding generation (duration, model)
  - Output guard flags (per flag type)
  - Session and token usage
  - Cost attribution per provider

All metrics are exposed on the standard ``/metrics`` endpoint via the
``prometheus-fastapi-instrumentator`` registered in ``backend/app.py``.
"""

from __future__ import annotations

import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, Info


# ─────────────────────────────────────────────────────────────────────────────
# Top-level AI request tracking
# ─────────────────────────────────────────────────────────────────────────────

# Counter: total AI requests received, by outcome
AI_REQUESTS = Counter(
    "ai_requests_total",
    "Total AI requests received by the backend",
    ["status"],  # status: success | scope_blocked | provider_error | timeout | error
)

# Histogram: end-to-end AI request duration (auth -> response stored)
AI_REQUEST_DURATION = Histogram(
    "ai_request_duration_seconds",
    "End-to-end AI request duration",
    ["status"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf")),
)

# Counter: AI requests that required at least one provider fallback
AI_REQUESTS_WITH_FALLBACK = Counter(
    "ai_requests_with_fallback_total",
    "AI requests that required at least one provider fallback",
)

# Gauge: number of AI requests currently being processed
AI_REQUESTS_IN_FLIGHT = Gauge(
    "ai_requests_in_flight",
    "AI requests currently being processed",
)


# ─────────────────────────────────────────────────────────────────────────────
# Scope gate (deterministic pre-LLM classifier)
# ─────────────────────────────────────────────────────────────────────────────

# Counter: scope gate decisions
AI_SCOPE_GATE_DECISIONS = Counter(
    "ai_scope_gate_decisions_total",
    "Scope gate decisions",
    ["decision", "category"],  # decision: in_scope | out_of_scope | injection
)

# Histogram: scope gate evaluation latency
AI_SCOPE_GATE_LATENCY = Histogram(
    "ai_scope_gate_latency_seconds",
    "Scope gate evaluation latency",
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, float("inf")),
)


# ─────────────────────────────────────────────────────────────────────────────
# Provider routing
# ─────────────────────────────────────────────────────────────────────────────

# Counter: per-provider request outcomes
AI_PROVIDER_REQUESTS = Counter(
    "ai_provider_requests_total",
    "AI provider requests",
    ["provider", "status"],  # status: success | fallback | error | timeout
)

# Histogram: per-provider latency
AI_PROVIDER_LATENCY = Histogram(
    "ai_provider_latency_seconds",
    "AI provider latency (per request)",
    ["provider"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf")),
)

# Counter: provider chain traversal events (used to compute fallback depth)
AI_PROVIDER_CHAIN_DEPTH = Histogram(
    "ai_provider_chain_depth",
    "Number of providers tried before getting a usable response",
    ["status"],
    buckets=(1, 2, 3, 4, 5, 6, 7, 8),
)

# Counter: provider configuration / mode
AI_PROVIDER_MODE_ACTIVE = Gauge(
    "ai_provider_mode_active",
    "1 if a given provider is configured as a candidate in the current mode",
    ["provider", "mode"],  # mode: mock | api | local | auto
)


# ─────────────────────────────────────────────────────────────────────────────
# RAG retrieval (pgvector)
# ─────────────────────────────────────────────────────────────────────────────

# Histogram: full RAG retrieval duration (embed + search + format)
AI_RAG_RETRIEVAL_DURATION = Histogram(
    "ai_rag_retrieval_duration_seconds",
    "RAG retrieval duration (embed + pgvector search + formatting)",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, float("inf")),
)

# Histogram: number of top-K chunks returned
AI_RAG_TOP_K_RESULTS = Histogram(
    "ai_rag_top_k_results_returned",
    "Number of top-K chunks returned by RAG retrieval",
    buckets=(0, 1, 2, 3, 5, 6, 8, 10, 15, 20),
)

# Histogram: top-1 cosine relevance score of returned chunks
AI_RAG_RELEVANCE_SCORE = Histogram(
    "ai_rag_relevance_score",
    "Cosine similarity of the top-1 retrieved chunk",
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

# Counter: RAG retrievals that returned zero results
AI_RAG_ZERO_RESULTS = Counter(
    "ai_rag_zero_results_total",
    "RAG retrievals that returned zero results (no chunk above min_score)",
    ["reason"],  # reason: below_threshold | no_documents | error
)

# Counter: RAG cache hits and misses (in-process LRU on query embeddings)
AI_RAG_CACHE_OPS = Counter(
    "ai_rag_cache_ops_total",
    "RAG embedding cache operations",
    ["result"],  # result: hit | miss
)

# Histogram: pgvector raw search latency (without embedding step)
AI_RAG_VECTOR_SEARCH_DURATION = Histogram(
    "ai_rag_vector_search_duration_seconds",
    "pgvector raw search latency",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float("inf")),
)

# Counter: RAG filter outcomes (domain / language / credibility filters)
AI_RAG_FILTER_OUTCOMES = Counter(
    "ai_rag_filter_outcomes_total",
    "RAG metadata filter outcomes",
    ["filter_name", "result"],  # result: kept | filtered
)


# ─────────────────────────────────────────────────────────────────────────────
# Embedding generation
# ─────────────────────────────────────────────────────────────────────────────

# Histogram: embedding generation duration
AI_EMBEDDING_DURATION = Histogram(
    "ai_embedding_duration_seconds",
    "Embedding generation duration",
    ["model"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf")),
)

# Counter: embedding generation outcomes
AI_EMBEDDING_REQUESTS = Counter(
    "ai_embedding_requests_total",
    "Embedding generation requests",
    ["model", "result"],  # result: success | error
)

# Gauge: currently loaded embedding models in memory
AI_EMBEDDING_MODELS_LOADED = Gauge(
    "ai_embedding_models_loaded",
    "Number of embedding models currently loaded in memory",
)


# ─────────────────────────────────────────────────────────────────────────────
# Output guard (post-generation safety)
# ─────────────────────────────────────────────────────────────────────────────

# Counter: output guard flags raised
AI_OUTPUT_GUARD_FLAGS = Counter(
    "ai_output_guard_flags_total",
    "Output guard flags raised by the post-generation validator",
    ["flag_type"],  # flag_type: prediction | financial_advice | code_block | jailbreak | disclaimer_missing | language_mismatch
)

# Histogram: output guard evaluation latency
AI_OUTPUT_GUARD_LATENCY = Histogram(
    "ai_output_guard_latency_seconds",
    "Output guard evaluation latency",
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, float("inf")),
)

# Counter: output guard severity breakdown
AI_OUTPUT_GUARD_SEVERITY = Counter(
    "ai_output_guard_severity_total",
    "Output guard flags by severity",
    ["severity"],  # severity: info | warning | error | critical
)


# ─────────────────────────────────────────────────────────────────────────────
# Chart action validation
# ─────────────────────────────────────────────────────────────────────────────

# Counter: chart action validation outcomes
AI_CHART_ACTIONS = Counter(
    "ai_chart_actions_total",
    "Chart action validation outcomes",
    ["action_type", "result"],  # result: accepted | rejected | invalid
)

# Histogram: chart action payload size
AI_CHART_ACTION_PAYLOAD_SIZE = Histogram(
    "ai_chart_action_payload_bytes",
    "Chart action payload size in bytes",
    ["action_type"],
    buckets=(10, 50, 100, 500, 1000, 5000, 10000, float("inf")),
)


# ─────────────────────────────────────────────────────────────────────────────
# Session, message and token tracking
# ─────────────────────────────────────────────────────────────────────────────

# Counter: AI chat sessions created
AI_CHAT_SESSIONS_CREATED = Counter(
    "ai_chat_sessions_created_total",
    "AI chat sessions created",
)

# Gauge: active AI chat sessions (last 24h, sliding)
AI_ACTIVE_SESSIONS = Gauge(
    "ai_active_sessions",
    "AI chat sessions active in the last 24 hours",
)

# Counter: AI messages stored
AI_MESSAGES_STORED = Counter(
    "ai_messages_stored_total",
    "AI messages stored in PostgreSQL",
    ["role"],  # role: user | assistant | system
)

# Counter: token usage
AI_TOKENS_USED = Counter(
    "ai_tokens_used_total",
    "Tokens used by AI providers",
    ["type", "provider"],  # type: input | output
)

# Histogram: token count per request
AI_TOKENS_PER_REQUEST = Histogram(
    "ai_tokens_per_request",
    "Token count per AI request (input + output)",
    ["type", "provider"],
    buckets=(50, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000, float("inf")),
)


# ─────────────────────────────────────────────────────────────────────────────
# Cost attribution
# ─────────────────────────────────────────────────────────────────────────────

# Counter: AI cost in USD (best-effort, depends on provider pricing)
AI_COST_USD = Counter(
    "ai_cost_usd_total",
    "Estimated AI cost in USD",
    ["provider"],
)

# Gauge: rolling 1h AI cost (computed via PromQL rate() in dashboards)
# (no direct gauge — this is a label-free derived metric in Grafana)


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge base health
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: total knowledge base chunks indexed
AI_KNOWLEDGE_CHUNKS_TOTAL = Gauge(
    "ai_knowledge_chunks_total",
    "Total chunks indexed in the RAG knowledge base",
    ["domain", "language", "credibility_level"],
)

# Gauge: total knowledge base documents
AI_KNOWLEDGE_DOCUMENTS_TOTAL = Gauge(
    "ai_knowledge_documents_total",
    "Total documents indexed in the RAG knowledge base",
    ["domain", "review_status"],
)

# Histogram: retrieval log write latency
AI_RETRIEVAL_LOG_LATENCY = Histogram(
    "ai_retrieval_log_latency_seconds",
    "Latency of writing the retrieval audit log entry",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, float("inf")),
)

# Counter: knowledge ingest events
AI_KNOWLEDGE_INGEST_EVENTS = Counter(
    "ai_knowledge_ingest_events_total",
    "Knowledge base ingest events",
    ["result"],  # result: success | error | rejected
)


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge base: extra gauges used by rag-knowledge-base dashboard
# ─────────────────────────────────────────────────────────────────────────────

# Gauge: total KB chunk count (label-free alias of the labeled
# ``ai_knowledge_chunks_total`` so dashboards can render a single
# stat without sum() aggregation).
AI_KNOWLEDGE_BASE_CHUNK_COUNT = Gauge(
    "ai_knowledge_base_chunk_count",
    "Total KB chunks (label-free alias of ai_knowledge_chunks_total)",
)

# Gauge: KB size in bytes
AI_KNOWLEDGE_BASE_SIZE_BYTES = Gauge(
    "ai_knowledge_base_size_bytes",
    "Total KB size in bytes (sum across all chunks)",
)

# Gauge: timestamp of the last successful ingest
AI_KNOWLEDGE_BASE_LAST_INGEST_TIMESTAMP = Gauge(
    "ai_knowledge_base_last_ingest_timestamp",
    "Unix timestamp of the last successful knowledge base ingest",
)

# Gauge: timestamp of the oldest chunk (used to compute data age)
AI_KNOWLEDGE_BASE_OLDEST_CHUNK_TIMESTAMP = Gauge(
    "ai_knowledge_base_oldest_chunk_timestamp",
    "Unix timestamp of the oldest chunk in the knowledge base",
)

# Gauge: embedding vector dimension (384 for MiniLM, 1536 for OpenAI, etc.)
AI_EMBEDDING_DIMENSIONS = Gauge(
    "ai_embedding_dimensions",
    "Embedding vector dimension used by the RAG pipeline",
    ["model"],
)

# Info: source / catalog info for the knowledge base (static labels)
AI_KNOWLEDGE_BASE_SOURCE_INFO = Info(
    "ai_knowledge_base_source",
    "Knowledge base source / catalog metadata (static labels)",
)

# Counter: total RAG retrievals (label-free alias)
AI_RAG_RETRIEVAL_TOTAL = Counter(
    "ai_rag_retrieval_total",
    "Total RAG retrieval operations",
)

# Counter: total retrieval audit log writes (label-free alias)
AI_RETRIEVAL_LOG_TOTAL = Counter(
    "ai_retrieval_log_total",
    "Total retrieval audit log writes",
    ["result"],  # result: success | failure
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def record_ai_request_start() -> None:
    """Mark an AI request as in-flight. Returns nothing; pair with finish()."""
    AI_REQUESTS_IN_FLIGHT.inc()


def record_ai_request_finish(
    status: str,
    duration_sec: float,
    had_fallback: bool = False,
) -> None:
    """Mark an AI request as finished and update its outcome metrics."""
    AI_REQUESTS.labels(status=status).inc()
    AI_REQUEST_DURATION.labels(status=status).observe(duration_sec)
    if had_fallback:
        AI_REQUESTS_WITH_FALLBACK.inc()
    AI_REQUESTS_IN_FLIGHT.dec()


def record_scope_gate(decision: str, category: str, duration_sec: float) -> None:
    """Record a scope gate decision."""
    AI_SCOPE_GATE_DECISIONS.labels(decision=decision, category=category).inc()
    AI_SCOPE_GATE_LATENCY.observe(duration_sec)


def record_provider_request(
    provider: str,
    status: str,
    duration_sec: float,
) -> None:
    """Record a per-provider request outcome."""
    AI_PROVIDER_REQUESTS.labels(provider=provider, status=status).inc()
    AI_PROVIDER_LATENCY.labels(provider=provider).observe(duration_sec)


def record_provider_chain_depth(depth: int, status: str) -> None:
    """Record how many providers were tried before getting a response."""
    AI_PROVIDER_CHAIN_DEPTH.labels(status=status).observe(depth)


def record_provider_mode_active(mode: str) -> None:
    """Mark the currently configured AI provider mode as active.

    Called from ``ProviderRouter.route_completion`` so dashboards can
    see whether the system is currently in ``local``, ``api``, ``none``,
    or ``auto`` mode (B13 observability).

    The ``AI_PROVIDER_MODE_ACTIVE`` gauge has labels
    ``(provider, mode)``; we set the active mode to 1 across all
    known providers so the dashboard can filter by mode alone.
    """
    for provider in ("local", "api", "none"):
        for m in ("local", "api", "none", "auto"):
            AI_PROVIDER_MODE_ACTIVE.labels(provider=provider, mode=m).set(0.0)
    for provider in ("local", "api", "none"):
        AI_PROVIDER_MODE_ACTIVE.labels(provider=provider, mode=mode).set(1.0)


def record_rag_vector_search(duration_sec: float = 0.0, success: bool = True) -> None:
    """Record RAG vector search timing."""
    pass  # Metrics placeholder


def record_rag_retrieval(
    duration_sec: float,
    n_results: int,
    top_score: Optional[float] = None,
    cache_hit: bool = False,
    vector_search_sec: Optional[float] = None,
) -> None:
    """Record a RAG retrieval outcome."""
    AI_RAG_RETRIEVAL_DURATION.observe(duration_sec)
    AI_RAG_TOP_K_RESULTS.observe(n_results)
    if top_score is not None:
        AI_RAG_RELEVANCE_SCORE.observe(top_score)
    if n_results == 0:
        AI_RAG_ZERO_RESULTS.labels(reason="below_threshold").inc()
    AI_RAG_CACHE_OPS.labels(result="hit" if cache_hit else "miss").inc()
    if vector_search_sec is not None:
        AI_RAG_VECTOR_SEARCH_DURATION.observe(vector_search_sec)


def record_embedding(model: str, duration_sec: float, success: bool = True) -> None:
    """Record embedding generation."""
    AI_EMBEDDING_DURATION.labels(model=model).observe(duration_sec)
    AI_EMBEDDING_REQUESTS.labels(
        model=model, result="success" if success else "error"
    ).inc()


def record_output_guard_flag(flag_type: str, severity: str = "warning", duration_sec: float = 0.0) -> None:
    """Record a single output guard flag."""
    AI_OUTPUT_GUARD_FLAGS.labels(flag_type=flag_type).inc()
    AI_OUTPUT_GUARD_SEVERITY.labels(severity=severity).inc()
    if duration_sec > 0:
        AI_OUTPUT_GUARD_LATENCY.observe(duration_sec)


def record_chart_action(action_type: str, result: str, payload_size: int) -> None:
    """Record a chart action validation outcome."""
    AI_CHART_ACTIONS.labels(action_type=action_type, result=result).inc()
    AI_CHART_ACTION_PAYLOAD_SIZE.labels(action_type=action_type).observe(payload_size)


def record_token_usage(provider: str, input_tokens: int, output_tokens: int) -> None:
    """Record token usage and per-request token counts."""
    AI_TOKENS_USED.labels(type="input", provider=provider).inc(input_tokens)
    AI_TOKENS_USED.labels(type="output", provider=provider).inc(output_tokens)
    AI_TOKENS_PER_REQUEST.labels(type="input", provider=provider).observe(input_tokens)
    AI_TOKENS_PER_REQUEST.labels(type="output", provider=provider).observe(output_tokens)


def record_ai_cost(provider: str, cost_usd: float) -> None:
    """Record estimated AI cost in USD for a provider."""
    AI_COST_USD.labels(provider=provider).inc(cost_usd)


def record_ai_session_created() -> None:
    """Record a new AI chat session creation."""
    AI_CHAT_SESSIONS_CREATED.inc()


def record_ai_message_stored(role: str) -> None:
    """Record a single AI message stored in PostgreSQL."""
    AI_MESSAGES_STORED.labels(role=role).inc()


def record_rag_filter(filter_name: str, kept: bool) -> None:
    """Record a single RAG filter outcome."""
    AI_RAG_FILTER_OUTCOMES.labels(
        filter_name=filter_name, result="kept" if kept else "filtered"
    ).inc()


def record_retrieval_log(duration_sec: float) -> None:
    """Record latency of writing a retrieval audit log entry."""
    AI_RETRIEVAL_LOG_LATENCY.observe(duration_sec)


def record_knowledge_ingest(result: str) -> None:
    """Record a knowledge base ingest event."""
    AI_KNOWLEDGE_INGEST_EVENTS.labels(result=result).inc()


# ─────────────────────────────────────────────────────────────────────────────
# KB inventory helpers (rag-knowledge-base dashboard)
# ─────────────────────────────────────────────────────────────────────────────

def record_kb_inventory(
    total_chunks: int,
    total_size_bytes: int,
    last_ingest_ts: float,
    oldest_chunk_ts: float,
    embedding_model: str = "all-MiniLM-L6-v2",
    embedding_dim: int = 384,
) -> None:
    """Update the knowledge-base inventory gauges in one shot.

    Called periodically (e.g. on each successful ingest) or via a
    background scheduler that scans the ``knowledge_chunks`` table.
    """
    AI_KNOWLEDGE_BASE_CHUNK_COUNT.set(total_chunks)
    AI_KNOWLEDGE_BASE_SIZE_BYTES.set(total_size_bytes)
    AI_KNOWLEDGE_BASE_LAST_INGEST_TIMESTAMP.set(last_ingest_ts)
    AI_KNOWLEDGE_BASE_OLDEST_CHUNK_TIMESTAMP.set(oldest_chunk_ts)
    AI_EMBEDDING_DIMENSIONS.labels(model=embedding_model).set(embedding_dim)
    AI_KNOWLEDGE_BASE_SOURCE_INFO.info({
        "embedding_model": embedding_model,
        "embedding_dim": str(embedding_dim),
        "index_type": "hnsw",
    })


def record_rag_retrieval_count(n: int = 1) -> None:
    """Increment the label-free RAG retrieval counter."""
    AI_RAG_RETRIEVAL_TOTAL.inc(n)


def record_retrieval_log_count(result: str = "success") -> None:
    """Increment the label-free retrieval-audit-log counter."""
    AI_RETRIEVAL_LOG_TOTAL.labels(result=result).inc()


__all__ = [
    # requests
    "AI_REQUESTS",
    "AI_REQUEST_DURATION",
    "AI_REQUESTS_WITH_FALLBACK",
    "AI_REQUESTS_IN_FLIGHT",
    # scope gate
    "AI_SCOPE_GATE_DECISIONS",
    "AI_SCOPE_GATE_LATENCY",
    # provider
    "AI_PROVIDER_REQUESTS",
    "AI_PROVIDER_LATENCY",
    "AI_PROVIDER_CHAIN_DEPTH",
    "AI_PROVIDER_MODE_ACTIVE",
    # RAG
    "AI_RAG_RETRIEVAL_DURATION",
    "AI_RAG_TOP_K_RESULTS",
    "AI_RAG_RELEVANCE_SCORE",
    "AI_RAG_ZERO_RESULTS",
    "AI_RAG_CACHE_OPS",
    "AI_RAG_VECTOR_SEARCH_DURATION",
    "AI_RAG_FILTER_OUTCOMES",
    # embedding
    "AI_EMBEDDING_DURATION",
    "AI_EMBEDDING_REQUESTS",
    "AI_EMBEDDING_MODELS_LOADED",
    # output guard
    "AI_OUTPUT_GUARD_FLAGS",
    "AI_OUTPUT_GUARD_LATENCY",
    "AI_OUTPUT_GUARD_SEVERITY",
    # chart actions
    "AI_CHART_ACTIONS",
    "AI_CHART_ACTION_PAYLOAD_SIZE",
    # session / tokens
    "AI_CHAT_SESSIONS_CREATED",
    "AI_ACTIVE_SESSIONS",
    "AI_MESSAGES_STORED",
    "AI_TOKENS_USED",
    "AI_TOKENS_PER_REQUEST",
    # cost
    "AI_COST_USD",
    # knowledge base
    "AI_KNOWLEDGE_CHUNKS_TOTAL",
    "AI_KNOWLEDGE_DOCUMENTS_TOTAL",
    "AI_RETRIEVAL_LOG_LATENCY",
    "AI_KNOWLEDGE_INGEST_EVENTS",
    # knowledge base inventory (rag-knowledge-base dashboard)
    "AI_KNOWLEDGE_BASE_CHUNK_COUNT",
    "AI_KNOWLEDGE_BASE_SIZE_BYTES",
    "AI_KNOWLEDGE_BASE_LAST_INGEST_TIMESTAMP",
    "AI_KNOWLEDGE_BASE_OLDEST_CHUNK_TIMESTAMP",
    "AI_EMBEDDING_DIMENSIONS",
    "AI_KNOWLEDGE_BASE_SOURCE_INFO",
    "AI_RAG_RETRIEVAL_TOTAL",
    "AI_RETRIEVAL_LOG_TOTAL",
    # helpers
    "record_ai_request_start",
    "record_ai_request_finish",
    "record_scope_gate",
    "record_provider_request",
    "record_provider_chain_depth",
    "record_provider_mode_active",
    "record_rag_retrieval",
    "record_embedding",
    "record_output_guard_flag",
    "record_chart_action",
    "record_token_usage",
    "record_ai_cost",
    "record_ai_session_created",
    "record_ai_message_stored",
    "record_rag_filter",
    "record_retrieval_log",
    "record_knowledge_ingest",
    "record_kb_inventory",
    "record_rag_retrieval_count",
    "record_retrieval_log_count",
]
