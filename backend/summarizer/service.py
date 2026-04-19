import os
from contextlib import asynccontextmanager

import aiosqlite


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "data/summarizer.db")
    if os.path.isabs(url):
        return url

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, url)


DATABASE_URL = get_database_url()
DATABASE_URL_RAW = os.environ.get("DATABASE_URL", "data/summarizer.db")


class Database:
    def __init__(self):
        self._db = None

    async def connect(self):
        if self._db:
            return

        db_dir = os.path.dirname(DATABASE_URL)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self._db = await aiosqlite.connect(DATABASE_URL)
        self._db.row_factory = aiosqlite.Row
        await self._init_schema()
        print(f"Connected to SQLite database at {DATABASE_URL}")

    async def _init_schema(self):
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT        PRIMARY KEY,
            email         TEXT,
            username      TEXT,
            first_name    TEXT,
            last_name     TEXT,
            created_at    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_email         ON users (email);
        CREATE INDEX IF NOT EXISTS idx_users_last_seen_at  ON users (last_seen_at DESC);

        CREATE TABLE IF NOT EXISTS summaries (
            id          TEXT        PRIMARY KEY,
            url         TEXT        NOT NULL,
            title       TEXT,
            summary     TEXT        NOT NULL,
            model       TEXT        NOT NULL DEFAULT 'openai/gpt-4o-mini',
            user_id     TEXT        NOT NULL DEFAULT 'guest_user',
            created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_summaries_url        ON summaries (url);
        CREATE INDEX IF NOT EXISTS idx_summaries_user_id    ON summaries (user_id);
        CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries (created_at DESC);
        """
        await self._db.executescript(schema)

        await self._ensure_summaries_user_id_is_text()
        await self._backfill_users_from_summaries()
        await self._db.commit()
        print("Schema initialised and verified")

    async def _ensure_summaries_user_id_is_text(self):
        async with self._db.execute("PRAGMA table_info(summaries)") as cursor:
            columns = await cursor.fetchall()

        user_id_col = next((column for column in columns if column["name"] == "user_id"), None)
        if user_id_col is None:
            await self._db.execute(
                "ALTER TABLE summaries ADD COLUMN user_id TEXT NOT NULL DEFAULT 'guest_user'"
            )
            return

        column_type = (user_id_col["type"] or "").upper()
        if "INT" not in column_type:
            return

        print("WARNING: summaries.user_id is INT. Converting to TEXT...")
        await self._db.executescript(
            """
            CREATE TABLE summaries_new (
                id          TEXT        PRIMARY KEY,
                url         TEXT        NOT NULL,
                title       TEXT,
                summary     TEXT        NOT NULL,
                model       TEXT        NOT NULL DEFAULT 'openai/gpt-4o-mini',
                user_id     TEXT        NOT NULL DEFAULT 'guest_user',
                created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO summaries_new (id, url, title, summary, model, user_id, created_at)
            SELECT id, url, title, summary, model, CAST(user_id AS TEXT), created_at
            FROM summaries;

            DROP TABLE summaries;
            ALTER TABLE summaries_new RENAME TO summaries;

            CREATE INDEX IF NOT EXISTS idx_summaries_url        ON summaries (url);
            CREATE INDEX IF NOT EXISTS idx_summaries_user_id    ON summaries (user_id);
            CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries (created_at DESC);
            """
        )
        print("Conversion to TEXT complete.")

    async def _backfill_users_from_summaries(self):
        await self._db.execute(
            "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
            ("guest_user", "guest"),
        )
        await self._db.executescript(
            """
            INSERT OR IGNORE INTO users (id)
            SELECT DISTINCT user_id
            FROM summaries
            WHERE user_id IS NOT NULL AND TRIM(CAST(user_id AS TEXT)) != '';
            """
        )

    async def disconnect(self):
        if not self._db:
            return
        await self._db.close()
        self._db = None

    @asynccontextmanager
    async def conn(self):
        if not self._db:
            await self.connect()
        yield self._db

    @property
    def DATABASE_URL(self):
        return DATABASE_URL

    @property
    def DATABASE_URL_RAW(self):
        return DATABASE_URL_RAW


db = Database()
