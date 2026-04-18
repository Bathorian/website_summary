# Website Summary

A web application that summarizes content from any URL using LLMs.

## Features
- **Backend**: FastAPI with `uv` for lightning-fast dependency management and builds.
- **Frontend**: Vue.js with Vite.
- **Database**: SQLite (local file or Docker volume).
- **LLM**: Powered by OpenRouter (GPT-4o-mini by default).

## Getting Started

### Prerequisites
- Docker & Docker Compose
- OpenRouter API Key

### Running with Docker
1. Set your `OPENROUTER_API_KEY` as an environment variable or in `docker-compose.yml`.
2. Start the services:
   ```bash
   docker compose up --build
   ```
3. Access the application:
   - Frontend: [http://localhost:8080](http://localhost:8080)
   - Backend API: [http://localhost:8000/docs](http://localhost:8000/docs)

## Development (Backend)
The backend uses [uv](https://github.com/astral-sh/uv).

### Installation
```bash
cd backend
uv sync
```

### Running Locally
```bash
cd backend
uv run uvicorn main:app --reload
```

## Database Migrations
The backend automatically applies migrations from `backend/migrations/*.up.sql` on startup. To modify the schema:
1. Add a new `.up.sql` file in `backend/migrations/` (e.g., `2_add_field.up.sql`).
2. Restart the backend service.