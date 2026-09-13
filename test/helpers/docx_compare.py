"""Сравнение содержимого .docx по нормализованному тексту (не побайтно)."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx_text(path: str | Path) -> str:
    """Извлекает весь текст из document.xml (параграфы и таблицы)."""
    path = Path(path)
    with ZipFile(path) as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    parts: list[str] = []
    for node in root.iter(f"{_W_NS}t"):
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return "".join(parts)


def normalize_docx_text(text: str) -> str:
    """Схлопывает пробелы/переносы для устойчивого сравнения."""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def docx_texts_equal(path_a: str | Path, path_b: str | Path) -> bool:
    return normalize_docx_text(extract_docx_text(path_a)) == normalize_docx_text(
        extract_docx_text(path_b)
    )


def assert_docx_contains(path: str | Path, *needles: str) -> None:
    text = normalize_docx_text(extract_docx_text(path))
    missing = [n for n in needles if n not in text]
    if missing:
        raise AssertionError(
            f"В {Path(path).name} не найдены фрагменты: {missing}. "
            f"Длина текста: {len(text)}"
        )
