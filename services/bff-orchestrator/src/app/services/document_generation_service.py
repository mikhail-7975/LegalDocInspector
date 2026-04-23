"""DOCX generation via legacy doc_creator (no edits to core templates logic)."""

from __future__ import annotations

from pathlib import Path

from LegalDocInspector.legal_doc_inspector.doc_creator.calculation_claim_generator import (
    CalculationClaimGenerator,
)
from LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator

from configs.config import AppConfig

from app.services.calculation_service import sort_data_structure


def generate_documents(
    *,
    config: AppConfig,
    claim_data: dict,
    calculator_list: list[dict],
    output_dir: Path,
    isk_filename: str,
    calculation_filename: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    isk_path = output_dir / isk_filename
    calc_path = output_dir / calculation_filename

    claim_gen = ClaimGenerator()
    claim_gen.make_instance(
        config=claim_data,
        template_filename=config.claim_template_path,
        output_filename=str(isk_path),
    )

    calc_claim_generator = CalculationClaimGenerator()
    calculator_list_sorted = [
        sort_data_structure(calculator_list[i]) for i in range(len(calculator_list))
    ]
    calc_claim_generator.make_instance(
        config=calculator_list_sorted,
        config2=claim_data,
        template_filename=config.calculation_claim_template_path,
        output_filename=str(calc_path),
    )

    return isk_path, calc_path
