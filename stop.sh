#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "[INFO] Stopping all ArthLens Docker Compose services..."
docker compose down

echo "[INFO] ArthLens services stopped."
