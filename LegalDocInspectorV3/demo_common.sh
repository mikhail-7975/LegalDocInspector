#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/infra/docker-compose.yml"

PY_CMD="${PY_CMD:-$(command -v python || command -v python3 || true)}"
if [[ -z "$PY_CMD" ]]; then
  echo "python not found"
  exit 1
fi

export PYTHONPATH="$ROOT"
export RABBITMQ_URL="${RABBITMQ_URL:-amqp://guest:guest@127.0.0.1:5672/}"

is_rabbitmq_available() {
  nc -z 127.0.0.1 5672 >/dev/null 2>&1 || (echo >/dev/tcp/127.0.0.1/5672) >/dev/null 2>&1
}

start_rabbitmq() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "RabbitMQ is not available and compose file was not found: $COMPOSE_FILE"
    return 1
  fi

  if command -v docker >/dev/null 2>&1; then
    echo "RabbitMQ is not available on 127.0.0.1:5672, starting via docker compose..."
    docker compose -f "$COMPOSE_FILE" up -d rabbitmq >/dev/null
  else
    echo "RabbitMQ is not available and docker is not installed."
    return 1
  fi

  for _ in {1..20}; do
    if is_rabbitmq_available; then
      echo "RabbitMQ is up on 127.0.0.1:5672"
      return 0
    fi
    sleep 1
  done

  echo "RabbitMQ did not become available on 127.0.0.1:5672 in time."
  return 1
}

ensure_rabbitmq() {
  if ! is_rabbitmq_available; then
    if ! start_rabbitmq; then
      echo "Please start RabbitMQ manually and re-run this script."
      exit 1
    fi
  fi

  if ! is_rabbitmq_available; then
    echo "RabbitMQ is still not available on 127.0.0.1:5672"
    exit 1
  fi
}
