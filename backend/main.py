import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env file from the project root or current directory
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))
load_dotenv(".env")

# Verify critical environment variables
if not os.environ.get("OPENROUTER_API_KEY"):
    print("WARNING: OPENROUTER_API_KEY is not set. Summarization will fail.")
if not os.environ.get("CLERK_SECRET_KEY"):
    print("WARNING: CLERK_SECRET_KEY is not set. All users will be 'guest_user'.")

from summarizer.api import router as summarizer_router
from summarizer.service import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    yield
    # Shutdown
    await db.disconnect()


app = FastAPI(title="URL Summarizer API", lifespan=lifespan)


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "https://distill-frontend-still-darkness-2746.fly.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(summarizer_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
