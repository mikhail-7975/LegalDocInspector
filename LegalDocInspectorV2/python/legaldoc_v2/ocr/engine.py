"""Интерфейс OCR-движка и загрузка из конфига (YAML в LegalDocInspectorV2/config)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

_log = logging.getLogger(__name__)


class PdfOcrMode(str, Enum):
    """Режимы, соответствующие проходам в существующем `parser_models` (претензия / договор)."""

    #: Первый проход претензии: Docling OCR, движок по умолчанию
    DEFAULT = "default"
    #: Договор и повтор претензии: EasyOCR, ru, full page
    EASYOCR_FULL_PAGE = "easyocr_full_page"


class OcrEngine(ABC):
    """Контракт: PDF → DoclingDocument (как в текущем пайплайне извлечения)."""

    @abstractmethod
    def convert_pdf(
        self,
        path: Path,
        *,
        mode: PdfOcrMode,
        page_range: tuple[int, int] | None = None,
    ) -> Any:
        """Возвращает `docling_core.types.doc.document.DoclingDocument`."""

    @abstractmethod
    def close(self) -> None:
        ...


def _config_path() -> Path:
    """Путь к ocr_engine.yaml: ``LegalDocInspectorV2/config/ocr_engine.yaml``."""
    here = Path(__file__).resolve()
    # .../LegalDocInspectorV2/python/legaldoc_v2/ocr/engine.py
    v2_root = here.parents[3]
    return v2_root / "config" / "ocr_engine.yaml"


def load_ocr_config(path: Path | None = None) -> dict[str, Any]:
    p = path or _config_path()
    if not p.is_file():
        raise FileNotFoundError(f"OCR config not found: {p}")
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("OCR config must be a YAML mapping")
    return data


def load_ocr_engine_from_config(
    config_path: Path | None = None,
    *,
    overrides: dict[str, Any] | None = None,
) -> OcrEngine:
    """
    Создаёт движок по `ocr_engine.yaml` (поле ``backend``).

    ``overrides`` — для тестов (например ``{"backend": "docling", "device": "cpu"}``).
    """
    cfg = load_ocr_config(config_path)
    if overrides:
        cfg = {**cfg, **overrides}
    backend = str(cfg.get("backend", "docling")).strip().lower()
    device = str(cfg.get("device", "cuda")).strip().lower()

    _log.info("OCR engine from config: backend=%s device=%s", backend, device)

    if backend == "docling":
        from legaldoc_v2.ocr.docling_backend import DoclingOcrEngine

        return DoclingOcrEngine(device_preference=device)

    raise ValueError(f"Неизвестный OCR backend в конфиге: {backend!r}. Поддерживается: docling")
