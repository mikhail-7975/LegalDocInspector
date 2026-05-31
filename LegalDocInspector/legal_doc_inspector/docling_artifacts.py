"""
Пути к предзагруженным моделям docling (offline / exe).

При сборке: vendor/docling-models → dist/.../models/
При запуске exe: DOCLING_ARTIFACTS_PATH и HF_HUB_OFFLINE задаются из pyi_rth_docling.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_WEIGHT_SUFFIXES = frozenset({".safetensors", ".pth", ".pt", ".bin", ".onnx"})


def _has_model_weights(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix.lower() in _WEIGHT_SUFFIXES:
            return True
    return False


def repo_root() -> Path:
    """Корень репозитория (родитель пакета LegalDocInspector)."""
    return Path(__file__).resolve().parents[2]


def vendor_models_dir() -> Path:
    return repo_root() / "vendor" / "docling-models"


def frozen_models_dir() -> Path:
    return Path(sys.executable).resolve().parent / "models"


def resolve_docling_artifacts_path() -> Path | None:
    """
    Каталог artifacts для docling или None, если локальные модели не найдены.
    Приоритет: DOCLING_ARTIFACTS_PATH → models/ рядом с exe → vendor/docling-models.
    """
    explicit = (os.environ.get("DOCLING_ARTIFACTS_PATH") or "").strip()
    if explicit:
        path = Path(explicit)
        if path.is_dir() and _has_model_weights(path):
            return path.resolve()

    if getattr(sys, "frozen", False):
        candidate = frozen_models_dir()
        if _has_model_weights(candidate):
            return candidate.resolve()

    vendor = vendor_models_dir()
    if _has_model_weights(vendor):
        return vendor.resolve()

    return None


def configure_docling_artifacts_env() -> Path | None:
    """Выставить DOCLING_ARTIFACTS_PATH и HF_HUB_OFFLINE, если models/ найдены."""
    path = resolve_docling_artifacts_path()
    if path is None:
        return None
    os.environ.setdefault("DOCLING_ARTIFACTS_PATH", str(path))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    return path
