"""
Реализация :class:`OcrEngine` на Docling — эквивалент настроек в существующем
``LegalDocInspector/.../pdf_parser/parser_models.py`` (PDFClaimParser / PDFContractParser):
- режим DEFAULT — пайплайн без явного EasyOcrOptions (первый проход претензии);
- режим EASYOCR_FULL_PAGE — EasyOcrOptions(lang=['ru'], force_full_page_ocr=True).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, ThreadedPdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline

from legaldoc_v2.ocr.engine import OcrEngine, PdfOcrMode

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument

_log = logging.getLogger(__name__)
logging.getLogger("docling").setLevel(logging.WARNING)


class DoclingOcrEngine(OcrEngine):
    def __init__(self, *, device_preference: str = "cuda") -> None:
        use_cuda = torch.cuda.is_available() and device_preference == "cuda"
        self._device = AcceleratorDevice.CUDA if use_cuda else AcceleratorDevice.CPU

        self._converter_default = self._make_converter(easyocr_full=False)
        self._converter_easyocr = self._make_converter(easyocr_full=True)

        t0 = time.time()
        self._converter_default.initialize_pipeline(InputFormat.PDF)
        self._converter_easyocr.initialize_pipeline(InputFormat.PDF)
        _log.info("DoclingOcrEngine: initialized in %.2fs", time.time() - t0)

    def _base_pipeline_options(self) -> ThreadedPdfPipelineOptions:
        return ThreadedPdfPipelineOptions(
            accelerator_options=AcceleratorOptions(
                device=self._device,
                num_threads=64,
            ),
            ocr_batch_size=4,
            layout_batch_size=16,
            table_batch_size=4,
            do_ocr=True,
            do_table_structure=True,
        )

    def _make_converter(self, *, easyocr_full: bool) -> DocumentConverter:
        opts = self._base_pipeline_options()
        if easyocr_full:
            opts.ocr_options = EasyOcrOptions(lang=["ru"], force_full_page_ocr=True)
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=opts,
                )
            }
        )

    def convert_pdf(
        self,
        path: Path,
        *,
        mode: PdfOcrMode,
        page_range: tuple[int, int] | None = None,
    ) -> Any:
        path = Path(path)
        conv = (
            self._converter_default
            if mode == PdfOcrMode.DEFAULT
            else self._converter_easyocr
        )
        _log.info(
            "DoclingOcrEngine.convert_pdf mode=%s path=%s page_range=%s",
            mode,
            path,
            page_range,
        )
        if page_range is not None:
            result = conv.convert(path, page_range=page_range)
        else:
            result = conv.convert(path)
        if result.status != ConversionStatus.SUCCESS:
            raise RuntimeError(f"Docling conversion failed: {path}")
        return result.document

    def close(self) -> None:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
