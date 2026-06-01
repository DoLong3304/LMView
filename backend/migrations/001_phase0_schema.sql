-- =============================================================================
-- Phase 0 Schema — LMView Auth + AI Foundation
-- Idempotent: safe to run multiple times.
-- Target database: lmview (or iceberg_catalog if sharing instance).
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── 1. users ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    username        TEXT UNIQUE,
    display_name    TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user'
                        CHECK (role IN ('user', 'admin', 'moderator')),
    preferred_language TEXT,
    timezone        TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- ── 2. auth_sessions ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS auth_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash  TEXT UNIQUE NOT NULL,
    user_agent          TEXT,
    ip_address          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ,
    last_seen_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash ON auth_sessions (session_token_hash);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions (expires_at);

-- ── 3. user_preferences ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    default_symbol      TEXT,
    default_timeframe   TEXT,
    default_exchange    TEXT DEFAULT 'binance',
    preferred_language  TEXT,
    theme               TEXT,
    risk_profile        TEXT,
    favorite_indicators JSONB NOT NULL DEFAULT '[]',
    ai_response_style   TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── 4. ai_chat_sessions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT,
    mode        TEXT NOT NULL DEFAULT 'ask'
                    CHECK (mode IN ('ask', 'interact')),
    symbol      TEXT,
    timeframe   TEXT,
    exchange    TEXT DEFAULT 'binance',
    status      TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'archived', 'deleted')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_sessions_user ON ai_chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_sessions_status ON ai_chat_sessions (status);

-- ── 5. ai_messages ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL
                        CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content         TEXT NOT NULL,
    language        TEXT,
    model_provider  TEXT,
    model_name      TEXT,
    token_input     INTEGER,
    token_output    INTEGER,
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_ai_messages_session ON ai_messages (session_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_user ON ai_messages (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_created ON ai_messages (created_at DESC);

-- ── 6. ai_chart_snapshots ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_chart_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id              UUID REFERENCES ai_chat_sessions(id) ON DELETE SET NULL,
    symbol                  TEXT NOT NULL,
    timeframe               TEXT NOT NULL,
    exchange                TEXT NOT NULL DEFAULT 'binance',
    chart_type              TEXT,
    visible_range_start     TIMESTAMPTZ,
    visible_range_end       TIMESTAMPTZ,
    selected_indicators     JSONB NOT NULL DEFAULT '[]',
    active_drawings         JSONB NOT NULL DEFAULT '[]',
    latest_candle           JSONB,
    market_context          JSONB NOT NULL DEFAULT '{}',
    data_freshness          JSONB NOT NULL DEFAULT '{}',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_chart_snapshots_user ON ai_chart_snapshots (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_chart_snapshots_session ON ai_chart_snapshots (session_id);

-- ── 7. ai_tool_actions ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_tool_actions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id          UUID REFERENCES ai_chat_sessions(id) ON DELETE SET NULL,
    message_id          UUID REFERENCES ai_messages(id) ON DELETE SET NULL,
    action_type         TEXT NOT NULL,
    action_payload      JSONB NOT NULL,
    validation_status   TEXT NOT NULL DEFAULT 'pending'
                            CHECK (validation_status IN ('pending', 'valid', 'invalid')),
    approval_status     TEXT NOT NULL DEFAULT 'not_required'
                            CHECK (approval_status IN ('not_required', 'pending', 'approved', 'rejected', 'edited')),
    execution_status    TEXT NOT NULL DEFAULT 'not_executed'
                            CHECK (execution_status IN ('not_executed', 'executed', 'failed')),
    reason              TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at         TIMESTAMPTZ,
    executed_at         TIMESTAMPTZ,
    error_message       TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_tool_actions_user ON ai_tool_actions (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_tool_actions_session ON ai_tool_actions (session_id);

-- ── 8. news_articles ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_articles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     TEXT,
    source          TEXT NOT NULL,
    title           TEXT NOT NULL,
    summary         TEXT,
    url             TEXT,
    published_at    TIMESTAMPTZ NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbols         JSONB NOT NULL DEFAULT '[]',
    tags            JSONB NOT NULL DEFAULT '[]',
    sentiment_score DOUBLE PRECISION,
    sentiment_label TEXT,
    language        TEXT,
    raw_payload     JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles (source);
CREATE INDEX IF NOT EXISTS idx_news_articles_sentiment ON news_articles (sentiment_label);
CREATE INDEX IF NOT EXISTS idx_news_articles_symbols ON news_articles USING GIN (symbols);

-- Dedupe: prevent duplicate articles from same source with same URL
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_articles_source_url
    ON news_articles (source, url)
    WHERE url IS NOT NULL;

-- ── 9. ai_knowledge_documents ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_knowledge_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type     TEXT NOT NULL,
    title           TEXT NOT NULL,
    uri             TEXT,
    content_hash    TEXT NOT NULL,
    language        TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'archived', 'deleted')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_docs_status ON ai_knowledge_documents (status);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_docs_source ON ai_knowledge_documents (source_type);

-- =============================================================================
-- Phase 1+ stubs (documented but not created):
--   - ai_knowledge_chunks (for RAG chunking)
--   - embedding vector columns (requires pgvector extension)
-- =============================================================================
