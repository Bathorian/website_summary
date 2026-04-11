import uuid
import os
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from .service import db
from .crawler import crawl_website
from .openrouter import summarize_content, DEFAULT_MODEL
from .auth import get_current_user
from fastapi import APIRouter, HTTPException, Depends, Request

router = APIRouter()

# ── Database Querier ─────────────────────────────────────────────────────────
class AsyncQuerier:
    def __init__(self, conn):
        self.conn = conn

    async def get_summary_by_url(self, url, user_id):
        query = "SELECT * FROM summaries WHERE url = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1"
        
        async with self.conn.execute(query, (url, user_id)) as cursor:
            return await cursor.fetchone()

    async def insert_summary(self, url, title, summary, model, user_id):
        uid = str(uuid.uuid4())
        print(f"DEBUG: Inserting summary for {url} with ID {uid} and user {user_id}")
        
        query = "INSERT INTO summaries (id, url, title, summary, model, user_id) VALUES (?, ?, ?, ?, ?, ?)"
        try:
            await self.conn.execute(query, (uid, url, title, summary, model, user_id))
            await self.conn.commit()
            async with self.conn.execute("SELECT * FROM summaries WHERE id = ?", (uid,)) as cursor:
                row = await cursor.fetchone()
                print(f"DEBUG: Inserted row in SQLite: {dict(row) if row else 'None'}")
                return row
        except Exception as e:
            print(f"ERROR: SQLite insertion failed: {e}")
            raise e

    async def list_summaries(self, user_id):
        query = "SELECT * FROM summaries WHERE user_id = ? ORDER BY created_at DESC LIMIT 50"
        async with self.conn.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            print(f"DEBUG: Listed {len(rows)} summaries for user {user_id}")
            return rows

    async def delete_summary(self, id, user_id):
        id_val = str(id)
        print(f"DEBUG: Deleting summary with ID {id_val} for user {user_id}")
        
        await self.conn.execute("DELETE FROM summaries WHERE id = ? AND user_id = ?", (id_val, user_id))
        await self.conn.commit()
        print(f"DEBUG: Deleted summary with ID {id_val}")


# ── Request / Response models ────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    url: HttpUrl
    model: Optional[str] = DEFAULT_MODEL
    force_refresh: Optional[bool] = False  # skip cache if True


class SummaryItem(BaseModel):
    id: str
    url: str
    title: Optional[str]
    summary: str
    model: str
    created_at: str


class SummarizeResponse(BaseModel):
    summary: SummaryItem
    cached: bool


class ListResponse(BaseModel):
    summaries: List[SummaryItem]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_to_item(row) -> SummaryItem:
    # SQLite row can be accessed by key
    created_at_val = row['created_at']
    # If it's a string from SQLite, use it, if it were a datetime we'd isoformat it
    if hasattr(created_at_val, 'isoformat'):
        created_at_val = created_at_val.isoformat()

    return SummaryItem(
        id=str(row['id']),
        url=row['url'],
        title=row['title'],
        summary=row['summary'],
        model=row['model'],
        created_at=created_at_val,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest, request: Request):
    user_id = await get_current_user(request)
    """
    Main endpoint: scrape a URL, summarise with an LLM, persist, and return.
    Uses a simple URL-level cache (last summary per URL) unless force_refresh.
    """
    url_str = str(req.url)
    if not url_str.endswith('/'):
        url_str += '/'

    # Check cache (brief connection)
    if not req.force_refresh:
        try:
            async with db.conn() as conn:
                q = AsyncQuerier(conn)
                existing = await q.get_summary_by_url(url=url_str, user_id=user_id)
                if existing:
                    return SummarizeResponse(
                        summary=_row_to_item(existing),
                        cached=True,
                    )
        except Exception as e:
            print(f"Cache check error: {e}")
            pass  # cache miss — proceed normally

    # Perform Crawl and LLM work OUTSIDE the database connection context
    # This prevents holding a database connection/lock for minutes during slow network work.
    
    # 1. Deep Spider Crawl: Scrape up to 11 pages with depth 1 (start URL + top 10 links)
    try:
        crawl_result = await crawl_website(url_str, max_pages=11, max_depth=1)
        if not crawl_result or crawl_result.get("title") == "Error":
            error_msg = crawl_result.get("markdown", "Unknown crawl error") if crawl_result else "No content found"
            raise Exception(error_msg)

        full_context = crawl_result["markdown"]
        # Global cap: 40,000 chars (approx 10-12k tokens) to ensure reliability
        if len(full_context) > 40000:
            print(f"API: Truncating context from {len(full_context)} to 40000 chars.")
            full_context = full_context[:40000] + "\n\n[... content truncated for token limits ...]"

        page_title = crawl_result["title"]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to crawl website: {exc}")

    # 2. Summarise with OpenRouter
    try:
        print(f"API: Sending {len(full_context)} chars of content to OpenRouter using {req.model or DEFAULT_MODEL}")
        summary_text = await summarize_content(
            content=full_context,
            title=f"Deep Crawl Summary for {page_title}",
            model=req.model or DEFAULT_MODEL,
        )
        print("API: Summarization successful")
    except Exception as exc:
        print(f"API: Summarization failed: {exc}")
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")

    # 3. Persist (brief connection again)
    try:
        async with db.conn() as conn:
            q = AsyncQuerier(conn)
            row = await q.insert_summary(
                url=url_str,
                title=page_title or "Untitled Crawler Result",
                summary=summary_text,
                model=req.model or DEFAULT_MODEL,
                user_id=user_id,
            )
            if not row:
                print(f"ERROR: insert_summary returned None for {url_str}")
                raise HTTPException(status_code=500, detail="Database insertion failed (no row returned)")
            
            summary_item = _row_to_item(row)
            print(f"DEBUG: Returning summary item: {summary_item.id}")
            return SummarizeResponse(summary=summary_item, cached=False)
    except Exception as e:
        print(f"ERROR: Database persistence failed for {url_str}: {e}")
        raise HTTPException(status_code=500, detail=f"Database persistence failed: {e}")


@router.get("/summaries", response_model=ListResponse)
async def list_summaries_endpoint(request: Request):
    user_id = await get_current_user(request)
    """Return the 50 most recent summaries."""
    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        rows = await q.list_summaries(user_id=user_id)
    return ListResponse(summaries=[_row_to_item(r) for r in rows])


@router.delete("/summaries/{id}")
async def delete_summary_endpoint(id: str, request: Request):
    user_id = await get_current_user(request)
    """Delete a summary by ID."""
    try:
        parsed_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        await q.delete_summary(id=parsed_id, user_id=user_id)
    return {"status": "ok"}


@router.get("/db-status")
async def db_status():
    """Diagnostic endpoint to check database connection status."""
    try:
        async with db.conn() as conn:
            # Check if we can query at all
            async with conn.execute("SELECT COUNT(*) FROM summaries") as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
            return {
                "status": "connected",
                "database_url": db.DATABASE_URL_RAW,
                "summary_count": count,
                "absolute_path": os.path.abspath(db.DATABASE_URL)
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
