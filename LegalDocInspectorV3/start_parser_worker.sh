#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

source "$ROOT/demo_common.sh"
ensure_rabbitmq

echo "Starting parser worker"
exec "$PY_CMD" -m demo_app.workers.parser_worker
