-- 007_tour_plans.sql
-- Persistence for Interact mode guided tour plans.
-- Allows replay and review of past AI-guided analysis tours.

-- Tour plans table: stores the plan, summary, and outcome
CREATE TABLE IF NOT EXISTS tour_plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
    tour_id         TEXT NOT NULL,        -- stable identifier (e.g. "lmview-overview", "indicator-tutorial", or auto-generated)
    title           TEXT NOT NULL,
    summary         TEXT,
    chart_snapshot  JSONB,                -- frozen chart context at tour start
    steps           JSONB NOT NULL,       -- array of TourStepAction objects
    current_step    INT NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'running', 'completed', 'cancelled')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    metadata        JSONB
);

-- Index for fast session-based lookups
CREATE INDEX IF NOT EXISTS idx_tour_plans_session ON tour_plans(session_id);
CREATE INDEX IF NOT EXISTS idx_tour_plans_status ON tour_plans(status);

-- Tour step execution log: records each step attempt
CREATE TABLE IF NOT EXISTS tour_step_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tour_plan_id    UUID NOT NULL REFERENCES tour_plans(id) ON DELETE CASCADE,
    step_index      INT NOT NULL,
    action_type     TEXT NOT NULL,
    params          JSONB,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'executing', 'completed', 'failed', 'skipped')),
    explanation     TEXT,
    result          TEXT,
    error           TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_tour_step_logs_plan ON tour_step_logs(tour_plan_id);

-- Track tour progress in ai_chat_sessions (optional embed)
ALTER TABLE ai_chat_sessions ADD COLUMN IF NOT EXISTS active_tour_plan_id UUID REFERENCES tour_plans(id);
