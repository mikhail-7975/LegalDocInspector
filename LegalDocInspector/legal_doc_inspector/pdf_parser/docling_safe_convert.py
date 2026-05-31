"""
Постраничная конвертация PDF с перехватом OOM / bad_alloc и частичным результатом.
"""

from __future__ import annotations

import gc
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Optional

import torch
from docling.datamodel.base_models import ConversionStatus
from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument

_log = logging.getLogger(__name__)


def is_allocation_error(exc: BaseException) -> bool:
    if isinstance(exc, MemoryError):
        return True
    msg = str(exc).lower()
    return (
        "bad_alloc" in msg
        or "out of memory" in msg
        or "cannot allocate" in msg
        or "alloc" in msg and "memory" in msg
    )


def release_memory() -> None:
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    gc.collect()


def get_pdf_page_count(pdf_path: Path) -> int:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page_count = len(pdf)
    finally:
        pdf.close()
    if page_count < 1:
        raise RuntimeError(f"PDF без страниц: {pdf_path}")
    return page_count


def convert_pdf_pages(
    doc_converter: DocumentConverter,
    pdf_path: Path,
    *,
    page_count: int | None = None,
    log_prefix: str = "PDF",
) -> tuple[list[DoclingDocument], int, Optional[BaseException]]:
    """
    Конвертирует PDF постранично. При OOM/bad_alloc возвращает уже обработанные страницы.
    """
    pdf_path = Path(pdf_path)
    page_count = page_count or get_pdf_page_count(pdf_path)
    documents: list[DoclingDocument] = []
    last_error: Optional[BaseException] = None

    for page_no in range(1, page_count + 1):
        _log.info(
            "%s: конвертация страницы %s/%s: %s",
            log_prefix,
            page_no,
            page_count,
            pdf_path,
        )
        try:
            conv_result = doc_converter.convert(
                pdf_path, page_range=(page_no, page_no)
            )
            if conv_result.status != ConversionStatus.SUCCESS:
                last_error = RuntimeError(
                    f"{log_prefix}: страница {page_no}/{page_count}, "
                    f"статус {conv_result.status}: {pdf_path}"
                )
                _log.warning("%s", last_error)
                break
            documents.append(conv_result.document)
        except Exception as exc:
            if is_allocation_error(exc):
                last_error = exc
                _log.warning(
                    "%s: OOM/bad_alloc на странице %s/%s, сохранено страниц: %s (%s)",
                    log_prefix,
                    page_no,
                    page_count,
                    len(documents),
                    exc,
                )
                break
            raise
        finally:
            release_memory()

    if last_error and documents:
        _log.warning(
            "%s: частичный результат — %s из %s страниц (%s)",
            log_prefix,
            len(documents),
            page_count,
            pdf_path,
        )
    return documents, len(documents), last_error


def concatenate_documents(
    documents: list[DoclingDocument],
) -> tuple[Optional[DoclingDocument], Optional[BaseException]]:
    if not documents:
        return None, None
    if len(documents) == 1:
        return documents[0], None
    try:
        return DoclingDocument.concatenate(documents), None
    except Exception as exc:
        if is_allocation_error(exc):
            _log.warning(
                "DoclingDocument.concatenate: OOM, остаётся %s отдельных документов",
                len(documents),
            )
            return None, exc
        raise


def documents_export_to_markdown(documents: list[DoclingDocument]) -> str:
    parts: list[str] = []
    for index, doc in enumerate(documents):
        try:
            parts.append(doc.export_to_markdown())
        except Exception as exc:
            if is_allocation_error(exc):
                _log.warning(
                    "export_to_markdown: OOM на фрагменте %s/%s, используется %s частей",
                    index + 1,
                    len(documents),
                    len(parts),
                )
                break
            raise
    return "\n\n".join(parts)


def documents_export_to_html(documents: list[DoclingDocument]) -> str:
    parts: list[str] = []
    for index, doc in enumerate(documents):
        try:
            parts.append(doc.export_to_html())
        except Exception as exc:
            if is_allocation_error(exc):
                _log.warning(
                    "export_to_html: OOM на фрагменте %s/%s, используется %s частей",
                    index + 1,
                    len(documents),
                    len(parts),
                )
                break
            raise
    return "\n".join(parts)


def documents_export_to_text(documents: list[DoclingDocument]) -> str:
    parts: list[str] = []
    for doc in documents:
        try:
            chunk = doc.export_to_text().strip()
            if chunk:
                parts.append(chunk)
                continue
            for block in doc.export_to_dict().get("texts") or []:
                if not isinstance(block, dict):
                    continue
                text = (block.get("text") or block.get("orig") or "").strip()
                if text:
                    parts.append(text)
        except Exception as exc:
            if is_allocation_error(exc):
                _log.warning(
                    "export_to_text: OOM, используется текст с %s страниц",
                    len(parts),
                )
                break
            raise
    return "\n\n".join(parts).strip()


def documents_have_text(documents: list[DoclingDocument]) -> bool:
    for doc in documents:
        try:
            if doc.export_to_text().strip():
                return True
            for block in doc.export_to_dict().get("texts") or []:
                if isinstance(block, dict) and (
                    (block.get("text") or "").strip()
                    or (block.get("orig") or "").strip()
                ):
                    return True
        except Exception as exc:
            if is_allocation_error(exc):
                continue
            raise
    return False


def extract_text_pairs_from_documents(
    documents: list[DoclingDocument],
    extract_text_with_page: Callable[[list], list[tuple[int, str]]],
) -> list[tuple[int, str]]:
    pairs: list[tuple[int, str]] = []
    for doc in documents:
        try:
            data = list(doc.export_to_dict().values())
            pairs.extend(extract_text_with_page(data))
        except Exception as exc:
            if is_allocation_error(exc):
                _log.warning(
                    "Извлечение text_pairs: OOM, сохранено блоков: %s",
                    len(pairs),
                )
                break
            raise
    return pairs
