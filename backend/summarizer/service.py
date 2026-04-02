import os
import aiosqlite
import asyncpg
import asyncio
from urllib.parse import urlparse
from contextlib import asynccontextmanager

# Database connection details from environment
# SQLite database file path or PostgreSQL URL
# Use absolute path for SQLite to avoid confusion based on CWD
def get_database_url():
    url = os.environ.get("DATABASE_URL", "data/summarizer.db")
    if url.startswith(("postgresql://", "postgres://")):
        return url
    
    # If it's a relative SQLite path, make it relative to the project root
    if not os.path.isabs(url):
        # We assume this file is in backend/summarizer/service.py
        # So project root is 2 levels up
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, url)
    return url

DATABASE_URL = get_database_url()
DATABASE_URL_RAW = os.environ.get("DATABASE_URL", "data/summarizer.db")

class Database:
    def __init__(self):
        self._db = None
        self._is_postgres = False

    async def connect(self):
        if not self._db:
            try:
                parsed = urlparse(DATABASE_URL)
                if parsed.scheme in ("postgresql", "postgres"):
                    self._is_postgres = True
                    self._db = await asyncpg.create_pool(DATABASE_URL)
                    print(f"Connected to PostgreSQL database at {parsed.netloc}")
                else:
                    self._is_postgres = False
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
        """Initialise the schema if it doesn't exist."""
        if self._is_postgres:
            schema = """
            CREATE TABLE IF NOT EXISTS summaries (
                id          UUID        PRIMARY KEY,
                url         TEXT        NOT NULL,
                title       TEXT,
                summary     TEXT        NOT NULL,
                model       TEXT        NOT NULL,
                created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_summaries_url        ON summaries (url);
            CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries (created_at DESC);
            """
            async with self._db.acquire() as conn:
                await conn.execute(schema)
        else:
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
            if self._is_postgres:
                await self._db.close()
            else:
                await self._db.close()
            self._db = None

    @asynccontextmanager
    async def conn(self):
        if not self._db:
            await self.connect()
        
        if self._is_postgres:
            async with self._db.acquire() as connection:
                yield connection
        else:
            yield self._db

    @property
    def is_postgres(self):
        return self._is_postgres

    @property
    def DATABASE_URL(self):
        return DATABASE_URL

    @property
    def DATABASE_URL_RAW(self):
        return DATABASE_URL_RAW

db = Database()
