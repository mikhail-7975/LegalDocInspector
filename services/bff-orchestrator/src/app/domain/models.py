from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.package_state import PackageState


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PackageRecord:
    package_id: str
    storage_path: Path
    state: PackageState = PackageState.created
    created_at: datetime = field(default_factory=utcnow)
    parse_result: dict[str, Any] | None = None
    extraction_error: str | None = None
    extraction_progress: dict[str, Any] = field(default_factory=dict)
    form_state: dict[str, Any] = field(default_factory=dict)
    calculation_result: dict[str, Any] | None = None
    doc_paths: dict[str, str] = field(default_factory=dict)
