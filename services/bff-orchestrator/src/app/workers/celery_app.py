"""Celery application (broker: RabbitMQ)."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root on sys.path (LegalDocInspector, configs)
_root = Path(__file__).resolve().parents[5]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from celery import Celery

from app.config import get_settings

settings = get_settings()

app = Celery(
    "legaldoc_bff",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend or "rpc://",
    include=["app.workers.tasks.extract_pipeline"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
