from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_legacy_repo_root() -> Path:
    # services/bff-orchestrator/src/app/config.py -> repo root
    return Path(__file__).resolve().parents[4]


def _default_storage_root() -> Path:
    return _default_legacy_repo_root() / "tmp" / "legaldoc-storage"


def _default_ocr_engine_config_path() -> Path:
    return _default_legacy_repo_root() / "LegalDocInspectorV2" / "config" / "ocr_engine.yaml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    legacy_repo_root: Path = Field(
        default_factory=_default_legacy_repo_root,
        description="Repository root containing LegalDocInspector/ and configs/",
    )
    storage_root: Path = Field(
        default_factory=_default_storage_root,
        description="File storage root (package folders)",
    )
    config_yaml: Path = Field(
        default_factory=lambda: Path("configs/debug_config.yaml"),
        description="Path to AppConfig YAML relative to legacy_repo_root or absolute",
    )
    ocr_engine_config_path: Path = Field(
        default_factory=_default_ocr_engine_config_path,
        description="LegalDocInspectorV2 OCR YAML (backend: docling, device: cuda|cpu)",
    )
    celery_broker_url: str = Field(default="amqp://guest:guest@localhost:5672//")
    celery_result_backend: Optional[str] = Field(default=None)
    session_secret: str = Field(default="dev-change-me")
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")
    default_admin_user: str = Field(default="admin")
    default_admin_password: str = Field(default="admin")
    package_ttl_hours: int = Field(default=8)
    max_complects: int = Field(default=30)
    max_certificates_per_complect: int = Field(default=20)


def get_settings() -> Settings:
    return Settings()
