import os
import aiosqlite
import asyncio
from contextlib import asynccontextmanager

# Database connection details from environment
# SQLite database file path
# Use absolute path for SQLite to avoid confusion based on CWD
def get_database_url():
    url = os.environ.get("DATABASE_URL", "data/summarizer.db")
    
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
        """Initialise the schema if it doesn't exist."""
        schema = """
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
        
    # Check if user_id exists, add if not (for existing databases)
        try:
            # We want to check the type as well. 
            # In SQLite, it's not easy to check type of existing column, 
            # but we can try to re-create or at least ensure it's not INT.
            # Migration 2 might have added it as INT.
            async with self._db.execute("PRAGMA table_info(summaries)") as cursor:
                columns = await cursor.fetchall()
                user_id_col = next((c for c in columns if c['name'] == 'user_id'), None)
                if user_id_col:
                    if 'INT' in user_id_col['type'].upper():
                        print("WARNING: user_id is INT. Converting to TEXT...")
                        # SQLite doesn't support easy ALTER COLUMN. 
                        # We must recreate the table with correct type.
                        await self._db.executescript("""
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
                            SELECT id, url, title, summary, model, CAST(user_id AS TEXT), created_at FROM summaries;
                            DROP TABLE summaries;
                            ALTER TABLE summaries_new RENAME TO summaries;
                            CREATE INDEX idx_summaries_url        ON summaries (url);
                            CREATE INDEX idx_summaries_user_id    ON summaries (user_id);
                            CREATE INDEX idx_summaries_created_at ON summaries (created_at DESC);
                        """)
                        print("Conversion to TEXT complete.")
                else:
                    await self._db.execute("ALTER TABLE summaries ADD COLUMN user_id TEXT NOT NULL DEFAULT 'guest_user'")
        except Exception as e:
            print(f"Error checking user_id column: {e}")
        
        await self._db.commit()
        print("Schema initialised and verified")

    async def disconnect(self):
        if self._db:
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
