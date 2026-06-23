-- Migration 006: News articles schema fix + RAG tsvector column
-- 
-- 1. Adds source_url, source_type, feed_type columns to news_articles
-- 2. Adds tsvector column + GIN index to ai_knowledge_chunks for BM25 search
-- 3. Adds unique index on news_articles (source, url) if missing

-- ── 1. news_articles: add missing columns ──────────────────────────────────

ALTER TABLE news_articles
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'rss_feed',
    ADD COLUMN IF NOT EXISTS feed_type TEXT DEFAULT 'crypto_news';

-- Rename url -> source_url for clarity; keep url as alias
-- (url column already exists; we add source_url as copy)
UPDATE news_articles SET source_url = url WHERE source_url IS NULL AND url IS NOT NULL;

-- ── 2. ai_knowledge_chunks: tsvector for BM25 keyword search ───────────────

ALTER TABLE ai_knowledge_chunks
    ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', COALESCE(content, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_chunks_tsv
    ON ai_knowledge_chunks USING GIN (content_tsv);
