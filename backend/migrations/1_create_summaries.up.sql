CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE summaries (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    url         TEXT        NOT NULL,
    title       TEXT,
    summary     TEXT        NOT NULL,
    model       TEXT        NOT NULL DEFAULT 'openai/gpt-4o-mini',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_summaries_url        ON summaries (url);
CREATE INDEX idx_summaries_created_at ON summaries (created_at DESC);
