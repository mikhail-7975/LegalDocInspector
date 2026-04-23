#!/usr/bin/env bash
# Запуск локального стека: RabbitMQ (опционально, Docker), API, Celery, Vite.
# Использование: ./run.sh   или   bash run.sh
# Флаги: --no-rabbit  — не поднимать контейнер RabbitMQ
#        --skip-install — не вызывать pip/npm install

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BFF_DIR="$ROOT/services/bff-orchestrator"
WEB_DIR="$ROOT/apps/web"
VENV_PY="$BFF_DIR/.venv/bin/python"
VENV_PIP="$BFF_DIR/.venv/bin/pip"
LOG_DIR="$ROOT/tmp/run-logs"
RABBIT_CONTAINER="${RABBIT_CONTAINER:-legaldoc-rabbitmq}"
SKIP_INSTALL=0
START_RABBIT=1

for arg in "$@"; do
  case "$arg" in
    --no-rabbit) START_RABBIT=0 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    -h|--help)
      echo "Usage: $0 [--no-rabbit] [--skip-install]"
      echo "  Starts RabbitMQ (Docker), uvicorn, Celery worker, Vite dev server."
      exit 0
      ;;
  esac
done

pick_python() {
  if command -v python3.12 >/dev/null 2>&1; then
    echo "python3.12"
  elif command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
  elif command -v python3.10 >/dev/null 2>&1; then
    echo "python3.10"
  elif command -v python3 >/dev/null 2>&1; then
    echo "python3"
  else
    echo "" >&2
    echo "Не найден Python 3.10+. Установите python3.12 или python3.11." >&2
    exit 1
  fi
}

PY="$(pick_python)"
export LEGACY_REPO_ROOT="$ROOT"
export STORAGE_ROOT="${STORAGE_ROOT:-$ROOT/tmp/legaldoc-storage}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-amqp://guest:guest@127.0.0.1:5672//}"
export PYTHONPATH="$ROOT:$BFF_DIR/src"
mkdir -p "$STORAGE_ROOT" "$LOG_DIR"

rabbit_listening() {
  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 5672 >/dev/null 2>&1
  else
    (echo >/dev/tcp/127.0.0.1/5672) >/dev/null 2>&1
  fi
}

ensure_rabbitmq() {
  if rabbit_listening; then
    echo "[run] RabbitMQ уже слушает порт 5672."
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "[run] Порт 5672 свободен, Docker не найден. Запустите RabbitMQ вручную или установите Docker." >&2
    exit 1
  fi
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$RABBIT_CONTAINER"; then
    echo "[run] Запуск контейнера $RABBIT_CONTAINER..."
    docker start "$RABBIT_CONTAINER"
  else
    echo "[run] Создание контейнера $RABBIT_CONTAINER (rabbitmq:3-management-alpine)..."
    docker run -d \
      --name "$RABBIT_CONTAINER" \
      -p 5672:5672 \
      -p 15672:15672 \
      rabbitmq:3-management-alpine
  fi
  echo "[run] Ожидание брокера..."
  for _ in $(seq 1 30); do
    rabbit_listening && return 0
    sleep 1
  done
  echo "[run] Таймаут: RabbitMQ не ответил на 5672." >&2
  exit 1
}

ensure_venv() {
  if [[ ! -x "$VENV_PY" ]]; then
    echo "[run] Создание venv в $BFF_DIR/.venv ($PY)..."
    "$PY" -m venv "$BFF_DIR/.venv"
  fi
  if [[ "$SKIP_INSTALL" -eq 0 ]]; then
    echo "[run] pip install (bff)..."
    "$VENV_PIP" install -U pip -q
    # requirements.txt: относительные пути (напр. -e ../../LegalDocInspectorV2/python) от каталога bff
    (cd "$BFF_DIR" && "$VENV_PIP" install -r requirements.txt -q)
    if [[ -f "$ROOT/requirements.txt" ]]; then
      echo "[run] pip install (корень репозитория, PDF/OCR) — может занять время..."
      "$VENV_PIP" install -r "$ROOT/requirements.txt" -q || {
        echo "[run] Предупреждение: не удалось установить корневой requirements.txt (частичный контур без OCR)." >&2
      }
    fi
  fi
}

ensure_npm() {
  if ! command -v npm >/dev/null 2>&1; then
    echo "[run] npm не найден. Установите Node.js 20 LTS." >&2
    exit 1
  fi
  if [[ "$SKIP_INSTALL" -eq 0 ]]; then
    if [[ -f "$WEB_DIR/package-lock.json" ]]; then
      (cd "$WEB_DIR" && npm ci)
    else
      (cd "$WEB_DIR" && npm install)
    fi
  fi
}

UVICORN_PID=""
CELERY_PID=""

cleanup() {
  set +e
  [[ -n "$CELERY_PID" ]] && kill "$CELERY_PID" 2>/dev/null
  [[ -n "$UVICORN_PID" ]] && kill "$UVICORN_PID" 2>/dev/null
  [[ -n "$CELERY_PID" ]] && wait "$CELERY_PID" 2>/dev/null
  [[ -n "$UVICORN_PID" ]] && wait "$UVICORN_PID" 2>/dev/null
  echo "[run] Остановлено."
}
trap cleanup EXIT INT TERM

if [[ "$START_RABBIT" -eq 1 ]]; then
  ensure_rabbitmq
else
  if ! rabbit_listening; then
    echo "[run] Предупреждение: порт 5672 не слушается — Celery не сможет подключиться." >&2
  fi
fi

ensure_venv
ensure_npm

echo "[run] API:   http://127.0.0.1:8000  (лог: $LOG_DIR/uvicorn.log)"
echo "[run] UI:    http://127.0.0.1:5173  (прокси /api → 8000)"
echo "[run] Ctrl+C — остановить все процессы."

(
  cd "$BFF_DIR"
  source .venv/bin/activate
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
) >"$LOG_DIR/uvicorn.log" 2>&1 &
UVICORN_PID=$!

(
  cd "$BFF_DIR"
  source .venv/bin/activate
  exec celery -A app.workers.celery_app worker --loglevel=INFO
) >"$LOG_DIR/celery.log" 2>&1 &
CELERY_PID=$!

sleep 1
if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
  echo "[run] Ошибка запуска API. См. $LOG_DIR/uvicorn.log" >&2
  tail -20 "$LOG_DIR/uvicorn.log" >&2 || true
  exit 1
fi

cd "$WEB_DIR"
npm run dev
