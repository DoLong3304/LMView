-- Migration 004: Multi-agent execution metadata
-- Supports LangGraph DAG orchestration, expert run traces, and FinBERT sentiment cache.
-- Additive only — does not alter existing tables.

-- ── Agent execution traces ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES ai_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    query TEXT NOT NULL,
    mode VARCHAR(16) DEFAULT 'ask',
    intent VARCHAR(64),
    activated_experts TEXT[],
    total_latency_ms INTEGER,
    total_token_input INTEGER DEFAULT 0,
    total_token_output INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(10, 6),
    confidence NUMERIC(4, 3),
    revision_count INTEGER DEFAULT 0,
    orchestration_mode VARCHAR(32) DEFAULT 'langgraph',
    provider VARCHAR(32),
    model_name VARCHAR(128),
    data_caveats TEXT[],
    warnings TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_executions_session
    ON ai_agent_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_user
    ON ai_agent_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_created
    ON ai_agent_executions(created_at DESC);

-- ── Expert run logs (one per expert per execution) ───────────────────────────
CREATE TABLE IF NOT EXISTS ai_expert_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES ai_agent_executions(id) ON DELETE CASCADE,
    expert_name VARCHAR(64) NOT NULL,
    latency_ms INTEGER,
    token_input INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    confidence NUMERIC(4, 3),
    output_summary TEXT,
    structured_data JSONB,
    data_sources TEXT[],
    status VARCHAR(16) DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expert_runs_execution
    ON ai_expert_runs(execution_id);
CREATE INDEX IF NOT EXISTS idx_expert_runs_expert
    ON ai_expert_runs(expert_name);

-- ── FinBERT sentiment cache ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_sentiment_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_hash VARCHAR(64) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source VARCHAR(128),
    url TEXT,
    sentiment_score NUMERIC(5, 4),
    sentiment_confidence NUMERIC(5, 4),
    sentiment_label VARCHAR(16),
    detected_entities TEXT[],
    event_category VARCHAR(64),
    affected_assets TEXT[],
    market_relevance NUMERIC(4, 3),
    analyzer VARCHAR(16) DEFAULT 'finbert',
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    article_published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sentiment_cache_hash
    ON news_sentiment_cache(article_hash);
CREATE INDEX IF NOT EXISTS idx_sentiment_cache_processed
    ON news_sentiment_cache(processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_cache_assets
    ON news_sentiment_cache USING GIN(affected_assets);

-- ── Agent performance metrics (aggregated daily) ─────────────────────────────
CREATE TABLE IF NOT EXISTS ai_agent_metrics_daily (
    metric_date DATE NOT NULL,
    orchestration_mode VARCHAR(32) NOT NULL DEFAULT 'langgraph',
    total_requests INTEGER DEFAULT 0,
    avg_latency_ms NUMERIC(10, 2),
    avg_confidence NUMERIC(4, 3),
    total_token_input BIGINT DEFAULT 0,
    total_token_output BIGINT DEFAULT 0,
    total_cost_usd NUMERIC(12, 6) DEFAULT 0,
    expert_activation_counts JSONB DEFAULT '{}',
    provider_usage_counts JSONB DEFAULT '{}',
    error_count INTEGER DEFAULT 0,
    revision_count INTEGER DEFAULT 0,
    PRIMARY KEY (metric_date, orchestration_mode)
);
