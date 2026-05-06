"""Генерация DOCX из эталонного create_doc_input.json (pytest)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.api.deps import load_app_config
from app.config import Settings
from app.services.document_generation_service import generate_documents

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATE_DOC_INPUT = (
    REPO_ROOT
    / "LegalDocInspectorV2"
    / "technical_specification"
    / "jsons"
    / "create_doc_input.json"
)

# CREATE_DOC_INPUT = Path("tmp/legaldoc-storage/fef90807-aa1d-48c9-9727-2e0fe3e1a522/create_doc_input.json")


@pytest.fixture
def app_config():
    settings = Settings(
        legacy_repo_root=REPO_ROOT,
        config_yaml=Path("configs/debug_config.yaml"),
    )
    return load_app_config(settings)


@pytest.fixture
def create_doc_input() -> dict:
    assert CREATE_DOC_INPUT.is_file(), f"Нет файла: {CREATE_DOC_INPUT}"
    return json.loads(CREATE_DOC_INPUT.read_text(encoding="utf-8"))


def test_generate_documents_from_create_doc_input(
    app_config, create_doc_input, tmp_path
):
    claim_data = create_doc_input["claim_data"]
    calculator_list = create_doc_input["calculator_list"]
    assert isinstance(calculator_list, list)
    assert len(calculator_list) >= 1
    assert all(isinstance(x, dict) for x in calculator_list)

    out_dir = tmp_path / "docgen_out"
    isk_path, calc_path = generate_documents(
        config=app_config,
        claim_data=claim_data,
        calculator_list=calculator_list,
        output_dir=out_dir,
        isk_filename="test_isk.docx",
        calculation_filename="test_calculation.docx",
    )

    assert isk_path.is_file()
    assert calc_path.is_file()
    assert isk_path.stat().st_size > 100
    assert calc_path.stat().st_size > 100
    assert isk_path.suffix == ".docx"
    assert calc_path.suffix == ".docx"
