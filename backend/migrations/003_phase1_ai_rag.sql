-- =============================================================================
-- Phase 1 AI RAG Schema — LMView Knowledge Base and Vector Search
-- Idempotent: safe to run multiple times.
-- Requires PostgreSQL 14+ with pgvector extension available.
-- =============================================================================

-- Enable pgvector for embedding storage and similarity search.
-- If pgvector is not installed, this will fail gracefully and the application
-- will operate without RAG capabilities.
CREATE EXTENSION IF NOT EXISTS vector;

-- ── 1. ai_knowledge_sources ─────────────────────────────────────────────────
-- Registry of knowledge base sources (markdown collections, doc sets, etc.)
CREATE TABLE IF NOT EXISTS ai_knowledge_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       TEXT UNIQUE NOT NULL,       -- human-readable unique identifier
    title           TEXT NOT NULL,
    description     TEXT,
    domain          TEXT NOT NULL DEFAULT 'general',
    language        TEXT NOT NULL DEFAULT 'en',
    source_type     TEXT NOT NULL DEFAULT 'internal_doc'
                        CHECK (source_type IN (
                            'internal_doc', 'technical_note', 'glossary',
                            'faq', 'tutorial', 'research_note', 'market_structure',
                            'risk_management', 'news_template', 'system_doc'
                        )),
    credibility_level TEXT NOT NULL DEFAULT 'verified'
                        CHECK (credibility_level IN ('verified', 'reviewed', 'draft', 'external')),
    review_status   TEXT NOT NULL DEFAULT 'approved'
                        CHECK (review_status IN ('approved', 'pending', 'rejected', 'deprecated')),
    allowed_for_rag BOOLEAN NOT NULL DEFAULT TRUE,
    version         TEXT NOT NULL DEFAULT '1.0.0',
    tags            JSONB NOT NULL DEFAULT '[]',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_sources_domain
    ON ai_knowledge_sources (domain);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_sources_status
    ON ai_knowledge_sources (review_status, allowed_for_rag);

-- ── 2. Extend existing ai_knowledge_documents ───────────────────────────────
-- Add columns needed for Phase 1 RAG without dropping existing data.
ALTER TABLE ai_knowledge_documents ADD COLUMN IF NOT EXISTS source_id UUID
    REFERENCES ai_knowledge_sources(id) ON DELETE SET NULL;
ALTER TABLE ai_knowledge_documents ADD COLUMN IF NOT EXISTS domain TEXT DEFAULT 'general';
ALTER TABLE ai_knowledge_documents ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]';
ALTER TABLE ai_knowledge_documents ADD COLUMN IF NOT EXISTS chunk_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE ai_knowledge_documents ADD COLUMN IF NOT EXISTS file_path TEXT;
ALTER TABLE ai_knowledge_documents ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER;

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_docs_source_id
    ON ai_knowledge_documents (source_id);

-- ── 3. ai_knowledge_chunks ──────────────────────────────────────────────────
-- Individual text chunks from documents, used for RAG retrieval.
CREATE TABLE IF NOT EXISTS ai_knowledge_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES ai_knowledge_documents(id) ON DELETE CASCADE,
    source_id       UUID REFERENCES ai_knowledge_sources(id) ON DELETE SET NULL,
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    content         TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    heading         TEXT,                        -- section heading this chunk belongs to
    language        TEXT DEFAULT 'en',
    token_count     INTEGER,
    char_count      INTEGER,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_chunks_doc
    ON ai_knowledge_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_chunks_source
    ON ai_knowledge_chunks (source_id);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_chunks_hash
    ON ai_knowledge_chunks (content_hash);

-- ── 4. ai_knowledge_embeddings ──────────────────────────────────────────────
-- Vector embeddings for each chunk. Uses pgvector's vector type.
-- Dimension 384 matches all-MiniLM-L6-v2; adjust if using a different model.
CREATE TABLE IF NOT EXISTS ai_knowledge_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id        UUID UNIQUE NOT NULL REFERENCES ai_knowledge_chunks(id) ON DELETE CASCADE,
    document_id     UUID NOT NULL REFERENCES ai_knowledge_documents(id) ON DELETE CASCADE,
    embedding       vector(384) NOT NULL,
    model_name      TEXT NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW index for fast approximate nearest-neighbor search.
-- cosine distance is standard for sentence-transformers models.
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_embeddings_vec
    ON ai_knowledge_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_embeddings_doc
    ON ai_knowledge_embeddings (document_id);

-- ── 5. ai_knowledge_retrieval_logs ──────────────────────────────────────────
-- Audit trail for RAG retrieval queries.
CREATE TABLE IF NOT EXISTS ai_knowledge_retrieval_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id      UUID REFERENCES ai_chat_sessions(id) ON DELETE SET NULL,
    message_id      UUID REFERENCES ai_messages(id) ON DELETE SET NULL,
    query_text      TEXT NOT NULL,
    query_embedding vector(384),
    top_k           INTEGER NOT NULL DEFAULT 6,
    min_score       DOUBLE PRECISION NOT NULL DEFAULT 0.25,
    filters         JSONB NOT NULL DEFAULT '{}',
    result_count    INTEGER NOT NULL DEFAULT 0,
    result_chunk_ids JSONB NOT NULL DEFAULT '[]',
    result_scores   JSONB NOT NULL DEFAULT '[]',
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_retrieval_logs_user
    ON ai_knowledge_retrieval_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_ai_retrieval_logs_session
    ON ai_knowledge_retrieval_logs (session_id);
CREATE INDEX IF NOT EXISTS idx_ai_retrieval_logs_created
    ON ai_knowledge_retrieval_logs (created_at DESC);

-- =============================================================================
-- End of Phase 1 AI RAG migration.
-- =============================================================================
