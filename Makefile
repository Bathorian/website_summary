.PHONY: backend frontend stop down status clean deploy-backend deploy-frontend deploy

# ─── Local Docker ───────────────────────────────────────────

# Start only the backend service
backend:
	docker compose up -d backend

# Start only the frontend service
frontend:
	docker compose up -d frontend

# Start all services
all:
	docker compose up -d

# Stop all running services
stop:
	docker compose stop

# Down all services and remove containers
down:
	docker compose down

# Check status of services
status:
	docker compose ps

# Clean up docker resources and orphans
clean:
	docker compose down --remove-orphans

# ─── Fly.io Deploy ──────────────────────────────────────────

# Deploy backend to Fly.io
deploy-backend:
	cd backend && fly deploy

deploy-frontend:
	cd frontend && fly deploy --build-arg VITE_API_URL=https://distill-backend.fly.dev

deploy:
	cd backend && fly deploy
	cd frontend && fly deploy --build-arg VITE_API_URL=https://distill-backend.fly.dev