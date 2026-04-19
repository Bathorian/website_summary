import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from .auth import CurrentUser, get_current_user
from .crawler import crawl_website
from .openrouter import DEFAULT_MODEL, summarize_content
from .service import db

router = APIRouter()


class AsyncQuerier:
    def __init__(self, conn):
        self.conn = conn

    async def upsert_user(self, user: CurrentUser):
        query = """
            INSERT INTO users (id, email, username, first_name, last_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email = COALESCE(excluded.email, users.email),
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_name = COALESCE(excluded.last_name, users.last_name),
                last_seen_at = CURRENT_TIMESTAMP
        """
        await self.conn.execute(
            query,
            (user.user_id, user.email, user.username, user.first_name, user.last_name),
        )
        await self.conn.commit()

    async def get_user(self, user_id: str):
        async with self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

    async def get_summary_by_url(self, url: str, user_id: str):
        query = "SELECT * FROM summaries WHERE url = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1"
        async with self.conn.execute(query, (url, user_id)) as cursor:
            return await cursor.fetchone()

    async def get_summary_by_id(self, summary_id: str, user_id: str):
        query = "SELECT id FROM summaries WHERE id = ? AND user_id = ? LIMIT 1"
        async with self.conn.execute(query, (summary_id, user_id)) as cursor:
            return await cursor.fetchone()

    async def insert_summary(self, url: str, title: str, summary: str, model: str, user_id: str):
        summary_id = str(uuid.uuid4())
        query = "INSERT INTO summaries (id, url, title, summary, model, user_id) VALUES (?, ?, ?, ?, ?, ?)"
        await self.conn.execute(query, (summary_id, url, title, summary, model, user_id))
        await self.conn.commit()
        async with self.conn.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,)) as cursor:
            return await cursor.fetchone()

    async def list_summaries(self, user_id: str, limit: int = 50):
        query = "SELECT * FROM summaries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        async with self.conn.execute(query, (user_id, limit)) as cursor:
            return await cursor.fetchall()

    async def delete_summary(self, summary_id: str, user_id: str):
        await self.conn.execute("DELETE FROM summaries WHERE id = ? AND user_id = ?", (summary_id, user_id))
        await self.conn.commit()


class SummarizeRequest(BaseModel):
    url: HttpUrl
    model: Optional[str] = DEFAULT_MODEL
    force_refresh: Optional[bool] = False


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


class UserItem(BaseModel):
    id: str
    email: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: str
    last_seen_at: str
    summary_count: int


class UserHistoryResponse(BaseModel):
    user: UserItem
    summaries: List[SummaryItem]


def _timestamp_to_string(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_to_item(row) -> SummaryItem:
    return SummaryItem(
        id=str(row["id"]),
        url=row["url"],
        title=row["title"],
        summary=row["summary"],
        model=row["model"],
        created_at=_timestamp_to_string(row["created_at"]),
    )


def _row_to_user(row, summary_count: int) -> UserItem:
    return UserItem(
        id=str(row["id"]),
        email=row["email"],
        username=row["username"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        created_at=_timestamp_to_string(row["created_at"]),
        last_seen_at=_timestamp_to_string(row["last_seen_at"]),
        summary_count=summary_count,
    )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    req: SummarizeRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    url_str = str(req.url)
    if not url_str.endswith("/"):
        url_str += "/"

    if not req.force_refresh:
        try:
            async with db.conn() as conn:
                q = AsyncQuerier(conn)
                await q.upsert_user(current_user)
                cached_row = await q.get_summary_by_url(url=url_str, user_id=current_user.user_id)
                if cached_row:
                    return SummarizeResponse(summary=_row_to_item(cached_row), cached=True)
        except Exception as exc:
            print(f"Cache check error: {exc}")

    try:
        crawl_result = await crawl_website(url_str, max_pages=11, max_depth=1)
        if not crawl_result or crawl_result.get("title") == "Error":
            error_msg = crawl_result.get("markdown", "Unknown crawl error") if crawl_result else "No content found"
            raise Exception(error_msg)

        full_context = crawl_result["markdown"]
        if len(full_context) > 40000:
            full_context = full_context[:40000] + "\n\n[... content truncated for token limits ...]"

        page_title = crawl_result["title"]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to crawl website: {exc}") from exc

    try:
        summary_text = await summarize_content(
            content=full_context,
            title=f"Deep Crawl Summary for {page_title}",
            model=req.model or DEFAULT_MODEL,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    try:
        async with db.conn() as conn:
            q = AsyncQuerier(conn)
            await q.upsert_user(current_user)
            row = await q.insert_summary(
                url=url_str,
                title=page_title or "Untitled Crawler Result",
                summary=summary_text,
                model=req.model or DEFAULT_MODEL,
                user_id=current_user.user_id,
            )

        if not row:
            raise HTTPException(status_code=500, detail="Database insertion failed")
        return SummarizeResponse(summary=_row_to_item(row), cached=False)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database persistence failed: {exc}") from exc


@router.get("/summaries", response_model=ListResponse)
async def list_summaries_endpoint(current_user: CurrentUser = Depends(get_current_user)):
    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        await q.upsert_user(current_user)
        rows = await q.list_summaries(user_id=current_user.user_id)
    return ListResponse(summaries=[_row_to_item(row) for row in rows])


@router.delete("/summaries/{id}")
async def delete_summary_endpoint(id: str, current_user: CurrentUser = Depends(get_current_user)):
    try:
        parsed_id = str(uuid.UUID(id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid UUID") from exc

    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        await q.upsert_user(current_user)
        existing = await q.get_summary_by_id(summary_id=parsed_id, user_id=current_user.user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Summary not found")
        await q.delete_summary(summary_id=parsed_id, user_id=current_user.user_id)
    return {"status": "ok"}


@router.get("/users/me", response_model=UserHistoryResponse)
async def get_my_profile_with_history(current_user: CurrentUser = Depends(get_current_user)):
    async with db.conn() as conn:
        q = AsyncQuerier(conn)
        await q.upsert_user(current_user)
        user_row = await q.get_user(current_user.user_id)
        rows = await q.list_summaries(user_id=current_user.user_id)

    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserHistoryResponse(
        user=_row_to_user(user_row, summary_count=len(rows)),
        summaries=[_row_to_item(row) for row in rows],
    )


@router.get("/db-status")
async def db_status():
    try:
        async with db.conn() as conn:
            async with conn.execute("SELECT COUNT(*) FROM summaries") as cursor:
                summary_row = await cursor.fetchone()
                summary_count = summary_row[0] if summary_row else 0

            async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
                user_row = await cursor.fetchone()
                user_count = user_row[0] if user_row else 0

            return {
                "status": "connected",
                "database_url": db.DATABASE_URL_RAW,
                "summary_count": summary_count,
                "user_count": user_count,
                "absolute_path": os.path.abspath(db.DATABASE_URL),
            }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }
