#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "=========================================================="
echo "           ARTHLENS UNIX RUNTIME ORCHESTRATOR             "
echo "=========================================================="

# 0. Ensure .env exists
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "[INFO] Created .env from .env.example"
fi

# 1. Start full stack via Docker Compose
echo "[1/3] Launching ArthLens full stack with Docker Compose..."
docker compose up -d --build

# 2. Wait for backend healthcheck
echo "[2/3] Waiting for FastAPI backend health check on http://127.0.0.1:8000/auth/ping..."
for i in {1..30}; do
    if curl -s -f http://127.0.0.1:8000/auth/ping > /dev/null 2>&1; then
        echo "      Backend is healthy and responsive."
        break
    fi
    sleep 1
done

# 3. Verify frontend readiness
echo "[3/3] Checking Next.js frontend on http://localhost:3000..."
for i in {1..30}; do
    if curl -s -f http://127.0.0.1:3000 > /dev/null 2>&1; then
        echo "      Frontend is responsive."
        break
    fi
    sleep 1
done

echo "=========================================================="
echo "        ARTHLENS APPLICATION OPERATIONAL AND READY        "
echo "=========================================================="
echo "  Frontend Web UI:   http://localhost:3000"
echo "  FastAPI Backend:   http://localhost:8000"
echo "  Interactive Docs:  http://localhost:8000/docs"
echo "  To stop:           ./stop.sh or docker compose down"
echo "=========================================================="
