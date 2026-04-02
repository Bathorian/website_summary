import os
import aiosqlite
import asyncio
from contextlib import asynccontextmanager

# Database connection details from environment
# SQLite database file path - use a persistent volume in docker
DATABASE_URL = os.environ.get("DATABASE_URL", "data/summarizer.db")

class Database:
    def __init__(self):
        self._db = None

    async def connect(self):
        if not self._db:
            try:
                # Ensure directory exists
                db_dir = os.path.dirname(DATABASE_URL)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)

                self._db = await aiosqlite.connect(DATABASE_URL)
                # Return rows as dictionaries
                self._db.row_factory = aiosqlite.Row
                print(f"Connected to SQLite database at {DATABASE_URL}")

                # Initialise schema
                await self._init_schema()
            except Exception as e:
                print(f"Failed to connect to database ({e}).")
                raise e

    async def _init_schema(self):
        """Initialise the SQLite schema if it doesn't exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS summaries (
            id          TEXT        PRIMARY KEY,
            url         TEXT        NOT NULL,
            title       TEXT,
            summary     TEXT        NOT NULL,
            model       TEXT        NOT NULL DEFAULT 'openai/gpt-4o-mini',
            created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_summaries_url        ON summaries (url);
        CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries (created_at DESC);
        """
        await self._db.executescript(schema)
        await self._db.commit()
        print("Schema initialised")

    async def disconnect(self):
        if self._db:
            await self._db.close()
            self._db = None

    @asynccontextmanager
    async def conn(self):
        if not self._db:
            await self.connect()
        yield self._db

db = Database()
