"""Общие фикстуры для тестов по папкам documents_from_request_*."""

from __future__ import annotations

from pathlib import Path

import pytest

from test.helpers.case_loader import (
    CASE_2026_06_17,
    case_files,
    load_result_parser,
    missing_generation_fields,
    resolve_generation_input,
)


@pytest.fixture(scope="session")
def case_2026_06_17_files() -> dict:
    return case_files(CASE_2026_06_17)


@pytest.fixture(scope="session")
def case_2026_06_17_result() -> dict:
    return load_result_parser(CASE_2026_06_17)


@pytest.fixture(scope="session")
def case_2026_06_17_generation() -> dict | None:
    return resolve_generation_input(CASE_2026_06_17)


@pytest.fixture
def require_generation_input(case_2026_06_17_generation):
    missing = missing_generation_fields(case_2026_06_17_generation)
    if missing:
        pytest.skip(
            "Недостаточно данных для генерации иска/расчёта: " + ", ".join(missing)
        )
    return case_2026_06_17_generation


@pytest.fixture(scope="session")
def app_config():
    from configs.config import load_yaml_config

    config_path = Path(__file__).resolve().parent.parent / "configs" / "debug_config.yaml"
    return load_yaml_config(str(config_path))


@pytest.fixture(scope="session")
def claim_parser():
    from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import (
        PDFClaimParser,
    )

    return PDFClaimParser()


@pytest.fixture(scope="session")
def contract_parser():
    from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import (
        PDFContractParser,
    )

    return PDFContractParser(device="cpu")
