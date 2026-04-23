from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_keys(data: dict[str, Any], required: set[str], cls_name: str) -> None:
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"{cls_name}: missing keys: {sorted(missing)}")
    extra = set(data.keys()) - required
    if extra:
        raise ValueError(f"{cls_name}: unknown keys: {sorted(extra)}")


@dataclass(frozen=True)
class InputFileRef:
    file_name: str
    file_type: str
    file_size: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "InputFileRef":
        keys = {"file_name", "file_type", "file_size"}
        _require_keys(data, keys, cls.__name__)
        return cls(
            file_name=str(data["file_name"]),
            file_type=str(data["file_type"]),
            file_size=int(data["file_size"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
        }


@dataclass(frozen=True)
class PackageData:
    application_date: str
    plaintiff_name: str
    defendant_name: str
    claim_amount: float
    files: list[InputFileRef]
    notes: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PackageData":
        keys = {
            "application_date",
            "plaintiff_name",
            "defendant_name",
            "claim_amount",
            "files",
            "notes",
        }
        _require_keys(data, keys, cls.__name__)
        files_raw = data["files"]
        if not isinstance(files_raw, list):
            raise ValueError("PackageData: 'files' must be list")
        return cls(
            application_date=str(data["application_date"]),
            plaintiff_name=str(data["plaintiff_name"]),
            defendant_name=str(data["defendant_name"]),
            claim_amount=float(data["claim_amount"]),
            files=[InputFileRef.from_json(x) for x in files_raw],
            notes=str(data["notes"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "application_date": self.application_date,
            "plaintiff_name": self.plaintiff_name,
            "defendant_name": self.defendant_name,
            "claim_amount": self.claim_amount,
            "files": [f.to_json() for f in self.files],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CommandMessage:
    id: str
    type: str
    package_id: str
    created_at: str
    payload: PackageData

    @classmethod
    def new(cls, msg_type: str, package_id: str, payload: PackageData) -> "CommandMessage":
        return cls(id=str(uuid4()), type=msg_type, package_id=package_id, created_at=_iso_now(), payload=payload)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CommandMessage":
        keys = {"id", "type", "package_id", "created_at", "payload"}
        _require_keys(data, keys, cls.__name__)
        if not isinstance(data["payload"], dict):
            raise ValueError("CommandMessage: 'payload' must be object")
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            package_id=str(data["package_id"]),
            created_at=str(data["created_at"]),
            payload=PackageData.from_json(data["payload"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "package_id": self.package_id,
            "created_at": self.created_at,
            "payload": self.payload.to_json(),
        }


@dataclass(frozen=True)
class ProgressMessage:
    id: str
    package_id: str
    stage: str
    progress: int
    status: str
    message: str
    timestamp: str

    @classmethod
    def new(cls, package_id: str, stage: str, progress: int, status: str, message: str) -> "ProgressMessage":
        return cls(
            id=str(uuid4()),
            package_id=package_id,
            stage=stage,
            progress=progress,
            status=status,
            message=message,
            timestamp=_iso_now(),
        )

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ProgressMessage":
        keys = {"id", "package_id", "stage", "progress", "status", "message", "timestamp"}
        _require_keys(data, keys, cls.__name__)
        return cls(
            id=str(data["id"]),
            package_id=str(data["package_id"]),
            stage=str(data["stage"]),
            progress=int(data["progress"]),
            status=str(data["status"]),
            message=str(data["message"]),
            timestamp=str(data["timestamp"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "package_id": self.package_id,
            "stage": self.stage,
            "progress": self.progress,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ResultMessage:
    id: str
    package_id: str
    status: str
    artifacts: list[str]
    timestamp: str

    @classmethod
    def new(cls, package_id: str, status: str, artifacts: list[str]) -> "ResultMessage":
        return cls(id=str(uuid4()), package_id=package_id, status=status, artifacts=artifacts, timestamp=_iso_now())

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ResultMessage":
        keys = {"id", "package_id", "status", "artifacts", "timestamp"}
        _require_keys(data, keys, cls.__name__)
        artifacts_raw = data["artifacts"]
        if not isinstance(artifacts_raw, list):
            raise ValueError("ResultMessage: 'artifacts' must be list")
        return cls(
            id=str(data["id"]),
            package_id=str(data["package_id"]),
            status=str(data["status"]),
            artifacts=[str(x) for x in artifacts_raw],
            timestamp=str(data["timestamp"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "package_id": self.package_id,
            "status": self.status,
            "artifacts": list(self.artifacts),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ErrorMessage:
    id: str
    package_id: str
    code: str
    message: str
    timestamp: str

    @classmethod
    def new(cls, package_id: str, code: str, message: str) -> "ErrorMessage":
        return cls(id=str(uuid4()), package_id=package_id, code=code, message=message, timestamp=_iso_now())

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ErrorMessage":
        keys = {"id", "package_id", "code", "message", "timestamp"}
        _require_keys(data, keys, cls.__name__)
        return cls(
            id=str(data["id"]),
            package_id=str(data["package_id"]),
            code=str(data["code"]),
            message=str(data["message"]),
            timestamp=str(data["timestamp"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "package_id": self.package_id,
            "code": self.code,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class UiEvent:
    event_type: str
    package_id: str
    data: dict[str, Any]
    timestamp: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "UiEvent":
        keys = {"event_type", "package_id", "data", "timestamp"}
        _require_keys(data, keys, cls.__name__)
        raw_data = data["data"]
        if not isinstance(raw_data, dict):
            raise ValueError("UiEvent: 'data' must be object")
        return cls(
            event_type=str(data["event_type"]),
            package_id=str(data["package_id"]),
            data=raw_data,
            timestamp=str(data["timestamp"]),
        )

    @classmethod
    def new(cls, event_type: str, package_id: str, data: dict[str, Any]) -> "UiEvent":
        return cls(event_type=event_type, package_id=package_id, data=data, timestamp=_iso_now())

    def to_json(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "package_id": self.package_id,
            "data": dict(self.data),
            "timestamp": self.timestamp,
        }
