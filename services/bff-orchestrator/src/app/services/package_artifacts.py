"""Снимки JSON (эталоны technical_specification/jsons/) в каталог пакета."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_parse_input_json(package_dir: Path, upload_meta: dict[str, Any]) -> None:
    """parse_input.json: date, complects_count, N_certificates_count."""
    payload: dict[str, str] = {
        "date": str(upload_meta.get("application_date", "")),
        "complects_count": str(upload_meta.get("complects_count", "")),
    }
    certs = upload_meta.get("certificates_per_complect") or []
    for idx, count in enumerate(certs, start=1):
        payload[f"{idx}_certificates_count"] = str(count)
    _write_json(package_dir / "parse_input.json", payload)


def save_parse_output_json(package_dir: Path, parse_result_api: dict[str, Any]) -> None:
    """parse_output.json — сериализованный разбор (как parse_result.json)."""
    _write_json(package_dir / "parse_output.json", parse_result_api)


def save_calculate_penalty_input_json(package_dir: Path, body: dict[str, Any]) -> None:
    """calculate_penalty_input.json — вход calculate_penalty."""
    _write_json(package_dir / "calculate_penalty_input.json", body)


def save_calculate_penalty_output_json(package_dir: Path, result: dict[str, Any]) -> None:
    """calculate_penalty_output.json — ответ run_calculate."""
    _write_json(package_dir / "calculate_penalty_output.json", result)


def save_create_calculating_table_input_json(
    package_dir: Path,
    result: dict[str, Any],
) -> None:
    """create_calculating_table_input.json — claim_data + calculator_list."""
    payload = {
        "claim_data": result.get("claim_data"),
        "calculator_list": result.get("calculator_list"),
    }
    _write_json(package_dir / "create_calculating_table_input.json", payload)


def save_create_doc_input_json(
    package_dir: Path,
    claim_data: dict[str, Any],
    calculator_list: list[Any],
    path_to_save: str,
) -> None:
    """create_doc_input.json — вход генерации DOCX."""
    payload: dict[str, Any] = {
        "claim_data": claim_data,
        "calculator_list": calculator_list,
        "path_to_save": path_to_save,
    }
    _write_json(package_dir / "create_doc_input.json", payload)
