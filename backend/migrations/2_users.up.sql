CREATE TABLE IF NOT EXISTS users (
    id            TEXT        PRIMARY KEY,
    email         TEXT,
    username      TEXT,
    first_name    TEXT,
    last_name     TEXT,
    created_at    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE summaries ADD COLUMN user_id TEXT NOT NULL DEFAULT 'guest_user';

CREATE INDEX IF NOT EXISTS idx_summaries_user_id ON summaries (user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
