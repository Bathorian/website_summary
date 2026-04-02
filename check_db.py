import os
import asyncio
from dotenv import load_dotenv
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Load .env
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from summarizer.service import db, DATABASE_URL

async def check_db():
    print("--- Database Connection Diagnostic ---")
    print(f"DATABASE_URL (resolved): {DATABASE_URL}")
    print(f"Absolute path (if SQLite): {os.path.abspath(DATABASE_URL)}")
    
    try:
        await db.connect()
        print("✅ Successfully connected to the database!")
        
        async with db.conn() as conn:
            if db.is_postgres:
                # PostgreSQL check
                res = await conn.fetchrow("SELECT COUNT(*) FROM summaries")
                count = res[0]
                print(f"✅ Table 'summaries' found in PostgreSQL. Rows: {count}")
            else:
                # SQLite check
                async with conn.execute("SELECT COUNT(*) FROM summaries") as cursor:
                    row = await cursor.fetchone()
                    count = row[0]
                    print(f"✅ Table 'summaries' found in SQLite. Rows: {count}")
        
        await db.disconnect()
        print("✅ Disconnected cleanly.")
    except Exception as e:
        print(f"❌ FAILED to connect: {e}")
        if "data/summarizer.db" in str(e):
            print("💡 Tip: Ensure the 'data' directory exists in your project root.")
    
    print("---------------------------------------")

if __name__ == "__main__":
    asyncio.run(check_db())
