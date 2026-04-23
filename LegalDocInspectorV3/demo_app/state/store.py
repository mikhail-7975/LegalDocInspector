from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from demo_app.models.messages import PackageData, UiEvent


@dataclass
class PackageRecord:
    package_id: str
    parsed_data: PackageData | None = None
    generated: bool = False


@dataclass
class InMemoryStore:
    packages: dict[str, PackageRecord] = field(default_factory=dict)
    events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def create_package(self, package_id: str) -> None:
        self.packages[package_id] = PackageRecord(package_id=package_id)
        self.events[package_id] = []

    def ensure_package(self, package_id: str) -> PackageRecord:
        rec = self.packages.get(package_id)
        if rec is None:
            raise KeyError(f"Package '{package_id}' not found")
        return rec

    def set_parsed_data(self, package_id: str, data: PackageData) -> None:
        rec = self.ensure_package(package_id)
        rec.parsed_data = data

    def mark_generated(self, package_id: str) -> None:
        rec = self.ensure_package(package_id)
        rec.generated = True

    def add_event(self, event: UiEvent) -> None:
        rec = self.ensure_package(event.package_id)
        _ = rec
        bucket = self.events[event.package_id]
        payload = event.to_json()
        payload["offset"] = len(bucket)
        bucket.append(payload)

    def get_events(self, package_id: str, since: int) -> list[dict[str, Any]]:
        self.ensure_package(package_id)
        return self.events[package_id][since:]


store = InMemoryStore()
