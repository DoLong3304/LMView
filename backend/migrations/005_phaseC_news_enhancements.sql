-- Phase C: News persistence enhancements
-- Idempotent migration for PostgreSQL-backed real news + sentiment fields.

ALTER TABLE news_articles
    ADD COLUMN IF NOT EXISTS content_snippet TEXT,
    ADD COLUMN IF NOT EXISTS sentiment_confidence DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS sentiment_computed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS symbols_mentioned TEXT[],
    ADD COLUMN IF NOT EXISTS raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS idx_news_source_external
    ON news_articles (source, external_id)
    WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_news_symbols_mentioned
    ON news_articles USING gin(symbols_mentioned);

CREATE INDEX IF NOT EXISTS idx_news_published_at
    ON news_articles (published_at DESC);
