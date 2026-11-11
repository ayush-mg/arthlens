.PHONY: help up down build migrate seed test test-backend test-frontend e2e lint clean

help:
	@echo "ArthLens One-Command Development Interface"
	@echo "  make up            - Launch full stack via Docker Compose (db, migrate, seed, backend, worker, frontend)"
	@echo "  make down          - Terminate and remove Docker Compose containers"
	@echo "  make build         - Build or rebuild Docker Compose service images"
	@echo "  make migrate       - Run latest Alembic database migrations"
	@echo "  make seed          - Seed demo and test user accounts"
	@echo "  make test          - Run full backend test suite"
	@echo "  make test-frontend - Run frontend unit and component tests"
	@echo "  make e2e           - Run Playwright end-to-end integration tests"
	@echo "  make lint          - Run backend and frontend code quality linters"
	@echo "  make clean         - Remove temporary artifacts and caches"

up:
	@if [ ! -f .env ] && [ -f .env.example ]; then cp .env.example .env; echo "Created .env from .env.example"; fi
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

migrate:
	alembic -c backend/alembic.ini upgrade head

seed:
	python scripts/seed_demo_accounts.py

test: test-backend

test-backend:
	pytest backend/tests backend/test

test-frontend:
	cd frontend && npm run test

e2e:
	cd frontend && npm run test:e2e

lint:
	ruff check backend
	cd frontend && npm run lint

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -f .arthlens-pids.json
