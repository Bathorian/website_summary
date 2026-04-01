from __future__ import annotations

import uuid
from typing import Optional

from encore.runtime.api import RequestContext
from pydantic import BaseModel, HttpUrl

from .service import db
from .scraper import scrape_url
from .openrouter import summarize_content, DEFAULT_MODEL

# ── sqlc-generated querier (created by: sqlc generate) ──────────────────────
try:
    from .db.query import AsyncQuerier
except ImportError:
    # Placeholder for when sqlc hasn't been run yet
    class AsyncQuerier:
        def __init__(self, conn):
            self.conn = conn
        async def get_summary_by_url(self, url): return None
        async def insert_summary(self, **kwargs): pass
        async def list_summaries(self): return []
        async def delete_summary(self, id): pass


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
    summaries: list[SummaryItem]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_to_item(row) -> SummaryItem:
    return SummaryItem(
        id=str(row.id),
        url=row.url,
        title=row.title,
        summary=row.summary,
        model=row.model,
        created_at=row.created_at.isoformat(),
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@api(method="POST", path="/summarize", expose=True, auth=False)
async def summarize(req: SummarizeRequest) -> SummarizeResponse:
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
            except Exception:
                pass  # cache miss — proceed normally

        # Scrape
        try:
            scraped = await scrape_url(url_str)
        except Exception as exc:
            raise APIError(400, f"Failed to scrape URL: {exc}") from exc

        if not scraped.content:
            raise APIError(422, "No readable content found at this URL.")

        # Summarise
        try:
            summary_text = await summarize_content(
                content=scraped.content,
                title=scraped.title,
                model=req.model or DEFAULT_MODEL,
            )
        except Exception as exc:
            raise APIError(502, f"LLM request failed: {exc}") from exc

        # Persist
        row = await q.insert_summary(
            url=url_str,
            title=scraped.title or None,
            summary=summary_text,
            model=req.model or DEFAULT_MODEL,
        )

    return SummarizeResponse(summary=_row_to_item(row), cached=False)


@api(method="GET", path="/summaries", expose=True, auth=False)
async def list_summaries() -> ListResponse:
    """Return the 20 most recent summaries."""
    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        rows = await q.list_summaries()
    return ListResponse(summaries=[_row_to_item(r) for r in rows])


@api(method="DELETE", path="/summaries/:id", expose=True, auth=False)
async def delete_summary(id: str) -> None:
    """Delete a summary by ID."""
    try:
        parsed_id = uuid.UUID(id)
    except ValueError as exc:
        raise APIError(400, "Invalid UUID") from exc

    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        await q.delete_summary(id=parsed_id)
