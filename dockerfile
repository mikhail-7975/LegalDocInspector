# syntax=docker/dockerfile:1.7
FROM python:3.13-slim AS builder

ARG UID=10001
ARG GID=10001

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl pkg-config \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /uvx /usr/local/bin/

# /app должен принадлежать uid:gid, иначе .venv не создастся
RUN install -d -o ${UID} -g ${GID} /app \
 && install -d -o ${UID} -g ${GID} /home/worker
WORKDIR /app

# метаданные проекта
COPY --chown=${UID}:${GID} pyproject.toml uv.lock README.md ./
USER ${UID}:${GID}
ENV HOME=/home/worker XDG_CACHE_HOME=/home/worker/.cache

RUN install -o ${UID} -g ${GID} -m 0644 /dev/null README.md
RUN --mount=type=cache,target=/home/worker/.cache,uid=10001,gid=10001,mode=0755 \
    uv venv && uv sync --frozen
# числовой пользователь + корректные HOME/CACHE
USER ${UID}:${GID}
ENV HOME=/home/worker \
    XDG_CACHE_HOME=/home/worker/.cache

# кэш uv в $XDG_CACHE_HOME (смонтирован с нужными uid/gid)
RUN --mount=type=cache,target=/home/worker/.cache,uid=10001,gid=10001,mode=0755 \
    uv venv && uv sync --frozen

FROM python:3.13-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr tesseract-ocr-rus \
 && rm -rf /var/lib/apt/lists/*

ARG UID=10001
ARG GID=10001
ENV HOME=/home/worker
RUN mkdir -p /app "${HOME}"

WORKDIR /app

# перенос venv и исходников с нужными владельцами
COPY --from=builder --chown=10001:10001 /app/.venv /app/.venv
# после COPY .venv
ENV PATH="/app/.venv/bin:${PATH}"

COPY --chown=10001:10001 . .

# работаем под числовым uid:gid
USER 10001:10001

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

CMD ["python", "run_fastapi.py"]
