import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env file from the project root (up one level from backend)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
# Also try current directory for Docker/local consistency
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


app.include_router(summarizer_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
