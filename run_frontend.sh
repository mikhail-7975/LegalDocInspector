#!/usr/bin/env bash
# Только фронтенд (Vite, apps/web). Прокси /api → http://127.0.0.1:8000 (см. vite.config.ts).
# Запуск API: VS Code «BFF: Uvicorn (debug)» или ./run.sh (без Vite в конце можно остановить).
#
# Использование: ./run_frontend.sh   или   bash run_frontend.sh
#   --skip-install  — не вызывать npm ci / npm install

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$ROOT/apps/web"
SKIP_INSTALL=0

for arg in "$@"; do
  case "$arg" in
    --skip-install) SKIP_INSTALL=1 ;;
    -h|--help)
      echo "Usage: $0 [--skip-install]"
      echo "  Starts Vite dev server on port 5173 (apps/web)."
      exit 0
      ;;
  esac
done

if ! command -v npm >/dev/null 2>&1; then
  echo "npm не найден. Установите Node.js." >&2
  exit 1
fi

cd "$WEB_DIR"
if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
fi

echo "[run_frontend] UI: http://127.0.0.1:5173  (API proxy → 8000)"
exec npm run dev
