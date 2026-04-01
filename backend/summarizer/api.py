import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl

from .service import db
from .scraper import scrape_url
from .openrouter import summarize_content, DEFAULT_MODEL

router = APIRouter()

# ── Mock Querier (since sqlc generated one might be missing) ──
class AsyncQuerier:
    def __init__(self, conn):
        self.conn = conn

    async def get_summary_by_url(self, url):
        return await self.conn.fetchrow(
            "SELECT * FROM summaries WHERE url = $1 ORDER BY created_at DESC LIMIT 1",
            url
        )

    async def insert_summary(self, url, title, summary, model):
        return await self.conn.fetchrow(
            "INSERT INTO summaries (url, title, summary, model) VALUES ($1, $2, $3, $4) RETURNING *",
            url, title, summary, model
        )

    async def list_summaries(self):
        return await self.conn.fetch(
            "SELECT * FROM summaries ORDER BY created_at DESC LIMIT 20"
        )

    async def delete_summary(self, id):
        await self.conn.execute("DELETE FROM summaries WHERE id = $1", id)


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
    return SummaryItem(
        id=str(row['id']),
        url=row['url'],
        title=row['title'],
        summary=row['summary'],
        model=row['model'],
        created_at=row['created_at'].isoformat(),
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest):
    """
    Main endpoint: scrape a URL, summarise with an LLM, persist, and return.
    Uses a simple URL-level cache (last summary per URL) unless force_refresh.
    """
    url_str = str(req.url)

    async with db.conn() as conn:
        q = AsyncQuerier(conn)

        # Check cache
        if not req.force_refresh:
            try:
                existing = await q.get_summary_by_url(url=url_str)
                if existing:
                    return SummarizeResponse(
                        summary=_row_to_item(existing),
                        cached=True,
                    )
            except Exception as e:
                print(f"Cache check error: {e}")
                pass  # cache miss — proceed normally

        # Scrape
        try:
            scraped = await scrape_url(url_str)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to scrape URL: {exc}")

        if not scraped.content:
            raise HTTPException(status_code=422, detail="No readable content found at this URL.")

        # Summarise
        try:
            summary_text = await summarize_content(
                content=scraped.content,
                title=scraped.title,
                model=req.model or DEFAULT_MODEL,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")

        # Persist
        row = await q.insert_summary(
            url=url_str,
            title=scraped.title or None,
            summary=summary_text,
            model=req.model or DEFAULT_MODEL,
        )

    return SummarizeResponse(summary=_row_to_item(row), cached=False)


@router.get("/summaries", response_model=ListResponse)
async def list_summaries_endpoint():
    """Return the 20 most recent summaries."""
    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        rows = await q.list_summaries()
    return ListResponse(summaries=[_row_to_item(r) for r in rows])


@router.delete("/summaries/{id}")
async def delete_summary_endpoint(id: str):
    """Delete a summary by ID."""
    try:
        parsed_id = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        await q.delete_summary(id=parsed_id)
    return {"status": "ok"}
