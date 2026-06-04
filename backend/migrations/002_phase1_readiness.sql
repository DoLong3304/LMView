-- =============================================================================
-- Phase 1 Readiness Schema - LMView account, settings, notifications, and
-- chart-action support.
-- Idempotent: safe to run multiple times.
-- =============================================================================

-- Extended user profile and account lifecycle fields.
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by_system BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_users_active_role ON users (is_active, role);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- Settings/preferences extension. JSONB keeps Phase 1 flexible without making
-- every frontend control a migration event.
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS notification_preferences JSONB NOT NULL DEFAULT '{
  "system": true,
  "alerts": true,
  "news": true,
  "ai": true,
  "sound": false,
  "desktop": false,
  "email": false,
  "position": "top-right"
}';

ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS customization_defaults JSONB NOT NULL DEFAULT '{
  "theme": "dark",
  "default_timeframe": "1m",
  "default_chart_type": "candles",
  "default_symbol": "BTCUSDT",
  "default_exchange": "binance",
  "visible_indicators": [],
  "drawing_defaults": {}
}';

ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS ai_settings JSONB NOT NULL DEFAULT '{
  "response_style": "concise",
  "risk_reminders": true,
  "auto_include_chart_context": true,
  "allow_chart_actions": false,
  "require_action_confirmation": true,
  "max_context_candles": 300,
  "memory_retention_days": 30
}';

ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS alert_settings JSONB NOT NULL DEFAULT '{
  "price_alerts": true,
  "volume_alerts": true,
  "indicator_alerts": true,
  "whale_alerts": true,
  "quiet_hours_enabled": false,
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "07:00"
}';

-- User notifications surfaced in the header popup.
CREATE TABLE IF NOT EXISTS user_notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category    TEXT NOT NULL DEFAULT 'system'
                    CHECK (category IN ('system', 'alert', 'news', 'ai')),
    severity    TEXT NOT NULL DEFAULT 'info'
                    CHECK (severity IN ('info', 'success', 'warning', 'error')),
    title       TEXT NOT NULL,
    body        TEXT,
    payload     JSONB NOT NULL DEFAULT '{}',
    read_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_notifications_user_created
    ON user_notifications (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_notifications_unread
    ON user_notifications (user_id, read_at)
    WHERE read_at IS NULL;

-- App-wide settings that admin debug can expose and alter.
CREATE TABLE IF NOT EXISTS app_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL DEFAULT '{}',
    scope       TEXT NOT NULL DEFAULT 'frontend'
                    CHECK (scope IN ('frontend', 'backend', 'system')),
    updated_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO app_settings (key, value, scope)
VALUES
    ('frontend.show_internal_status', 'false', 'frontend'),
    ('frontend.notifications_enabled', 'true', 'frontend'),
    ('frontend.chart_action_testing', 'true', 'frontend')
ON CONFLICT (key) DO NOTHING;

-- Watchlist activity cache. Backend ticker responses also compute activity live
-- from ticker fields; this table is for future persisted activity overrides.
CREATE TABLE IF NOT EXISTS watchlist_activity (
    exchange       TEXT NOT NULL DEFAULT 'binance',
    symbol         TEXT NOT NULL,
    activity_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    volume_24h     DOUBLE PRECISION,
    change_24h     DOUBLE PRECISION,
    trade_count    BIGINT,
    last_event_time BIGINT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (exchange, symbol)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_activity_score
    ON watchlist_activity (activity_score DESC, symbol);

-- AI context/session extension.
ALTER TABLE ai_chat_sessions ADD COLUMN IF NOT EXISTS context_summary JSONB NOT NULL DEFAULT '{}';
ALTER TABLE ai_chat_sessions ADD COLUMN IF NOT EXISTS memory_policy JSONB NOT NULL DEFAULT '{}';
ALTER TABLE ai_tool_actions ADD COLUMN IF NOT EXISTS client_action_id TEXT;
ALTER TABLE ai_tool_actions ADD COLUMN IF NOT EXISTS target_descriptor JSONB NOT NULL DEFAULT '{}';
