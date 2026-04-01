import os
import asyncpg
import asyncio
from contextlib import asynccontextmanager

# Database connection details from environment
# For local dev without docker, use localhost:5433
# Inside docker, DATABASE_URL should be set to postgresql://user:password@db:5432/summarizer
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5433/summarizer")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            retries = 5
            while retries > 0:
                try:
                    self.pool = await asyncpg.create_pool(DATABASE_URL)
                    print("Connected to database")
                    break
                except Exception as e:
                    retries -= 1
                    print(f"Failed to connect to database ({e}). Retrying in 2 seconds... ({retries} retries left)")
                    if retries == 0:
                        raise e
                    await asyncio.sleep(2)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def conn(self):
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as connection:
            yield connection

db = Database()
