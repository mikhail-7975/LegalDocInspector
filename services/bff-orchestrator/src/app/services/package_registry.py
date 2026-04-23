from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models import PackageRecord


class PackageRegistry:
    def __init__(self) -> None:
        self._data: dict[str, PackageRecord] = {}
        self._lock = threading.Lock()

    def get(self, package_id: str) -> PackageRecord | None:
        with self._lock:
            return self._data.get(package_id)

    def put(self, record: PackageRecord) -> None:
        with self._lock:
            self._data[record.package_id] = record

    def update_state(self, package_id: str, **kwargs: object) -> PackageRecord | None:
        with self._lock:
            rec = self._data.get(package_id)
            if not rec:
                return None
            for k, v in kwargs.items():
                setattr(rec, k, v)
            return rec


registry = PackageRegistry()
