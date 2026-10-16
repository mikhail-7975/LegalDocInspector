#!/usr/bin/env python3
"""
Пункт 1 плана PDF-парсера: sidecar HTML рядом с каждым PDF в test/data
и baseline extract vs generation_input для договоров.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import load_yaml_config
from LegalDocInspector.legal_doc_inspector.pdf_parser.docling_safe_convert import (
    convert_pdf_pages,
    documents_export_to_html,
    get_pdf_page_count,
    sidecar_html_path,
    write_pdf_sidecar_html,
)
from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import (
    PDFClaimParser,
    PDFContractParser,
    _docling_pipeline_options_low_memory,
)
from LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate import (
    extract_text_from_pdf,
)
from test.helpers.case_loader import case_files, list_case_names, load_generation_input


def _iter_test_pdfs() -> list[Path]:
    root = ROOT / "test" / "data"
    paths: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix.lower() == ".pdf" or p.name.lower() == "pdf":
            paths.append(p)
    return sorted(paths)


def _generic_dump_html(pdf_path: Path) -> Path:
    """Конвертация PDF → sidecar HTML без эвристик договора/претензии."""
    import torch
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline

    pipeline_options = _docling_pipeline_options_low_memory(
        use_cuda=torch.cuda.is_available()
    )
    pipeline_options.do_ocr = False
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=ThreadedStandardPdfPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )
    converter.initialize_pipeline(InputFormat.PDF)
    page_count = get_pdf_page_count(pdf_path)
    documents, pages_ok, last_error = convert_pdf_pages(
        converter,
        pdf_path,
        page_count=page_count,
        log_prefix="sidecar-dump",
    )
    if not documents:
        # fallback OCR via claim/contract style converter with OCR on
        from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import (
            _tesseract_cli_ocr_options,
        )

        pipeline_options = _docling_pipeline_options_low_memory(
            use_cuda=torch.cuda.is_available()
        )
        pipeline_options.ocr_options = _tesseract_cli_ocr_options()
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )
        converter.initialize_pipeline(InputFormat.PDF)
        documents, pages_ok, last_error = convert_pdf_pages(
            converter,
            pdf_path,
            page_count=page_count,
            log_prefix="sidecar-dump-OCR",
        )
    if not documents:
        raise RuntimeError(f"Не удалось сконвертировать {pdf_path}: {last_error}")
    return write_pdf_sidecar_html(pdf_path, documents_export_to_html(documents))


def main() -> int:
    config = load_yaml_config(str(ROOT / "configs" / "debug_config.yaml"))
    contract_parser = PDFContractParser(device="cpu")
    claim_parser = PDFClaimParser()

    handled: set[Path] = set()
    baseline_rows: list[dict] = []

    for case_name in list_case_names():
        files = case_files(case_name)
        gen = load_generation_input(case_name) or {}
        ui_complects = gen.get("complects") or []

        if files.get("egrul_pdf") and files["egrul_pdf"].is_file():
            p = files["egrul_pdf"].resolve()
            print(f"[egrul] {p}")
            try:
                extract_text_from_pdf(p)
                handled.add(p)
            except Exception as exc:
                print(f"  FAIL egrul: {exc}")

        for i, meta in enumerate(files.get("complects") or []):
            ui = ui_complects[i] if i < len(ui_complects) else {}
            if meta.get("contract_pdf") and meta["contract_pdf"].is_file():
                p = meta["contract_pdf"].resolve()
                print(f"[contract] {p}")
                try:
                    ctype, cpoint, day, _ = contract_parser.analyse_contract(p, config)
                    handled.add(p)
                    baseline_rows.append(
                        {
                            "case": case_name,
                            "complect": i + 1,
                            "pdf": str(p.relative_to(ROOT)),
                            "extracted_type": ctype,
                            "expected_type": ui.get("contract_type"),
                            "extracted_point": cpoint,
                            "expected_point": ui.get("contract_point"),
                            "extracted_day": day,
                            "expected_day": ui.get("day_of_penalty"),
                            "html": str(sidecar_html_path(p).relative_to(ROOT)),
                        }
                    )
                except Exception as exc:
                    print(f"  FAIL contract: {exc}")
                    baseline_rows.append(
                        {
                            "case": case_name,
                            "complect": i + 1,
                            "pdf": str(p.relative_to(ROOT)),
                            "extracted_type": f"ERROR: {exc}",
                            "expected_type": ui.get("contract_type"),
                            "extracted_point": "",
                            "expected_point": ui.get("contract_point"),
                            "extracted_day": "",
                            "expected_day": ui.get("day_of_penalty"),
                            "html": "",
                        }
                    )
            if meta.get("claim_pdf") and meta["claim_pdf"].is_file():
                p = meta["claim_pdf"].resolve()
                print(f"[claim] {p}")
                try:
                    claim_parser.analyse_claim(p)
                    handled.add(p)
                except Exception as exc:
                    print(f"  FAIL claim: {exc}")

    # оставшиеся PDF (не попали в case_files)
    for pdf in _iter_test_pdfs():
        resolved = pdf.resolve()
        if resolved in handled:
            continue
        print(f"[generic] {resolved}")
        try:
            _generic_dump_html(resolved)
            handled.add(resolved)
        except Exception as exc:
            print(f"  FAIL generic: {exc}")

    out_csv = ROOT / "test" / "data" / "contract_parser_baseline.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case",
                "complect",
                "pdf",
                "extracted_type",
                "expected_type",
                "extracted_point",
                "expected_point",
                "extracted_day",
                "expected_day",
                "html",
            ],
        )
        writer.writeheader()
        writer.writerows(baseline_rows)

    html_count = sum(
        1 for p in _iter_test_pdfs() if sidecar_html_path(p).is_file()
    )
    print(f"\nBaseline CSV: {out_csv}")
    print(f"PDF total: {len(_iter_test_pdfs())}, HTML present: {html_count}")
    print(f"Contract rows: {len(baseline_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
