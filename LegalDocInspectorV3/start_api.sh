#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

source "$ROOT/demo_common.sh"
ensure_rabbitmq

echo "Starting API on http://127.0.0.1:8001"
exec "$PY_CMD" -m uvicorn demo_app.api.main:app --host 0.0.0.0 --port 8001
