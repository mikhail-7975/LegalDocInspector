"""Загрузка тестовых кейсов documents_from_request_* и проверка generation_input."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any


CASE_2026_06_17 = "documents_from_request_2026-06-17_160359.877789"

REQUIRED_GENERATION_FIELDS = (
    "company_type",
    "end_date",
    "responsitive_name",
)

REQUIRED_PLAINTIFF_FIELDS = (
    "full_name",
    "short_name",
    "addres",
    "ogrn",
    "inn",
)

# Маркеры «парсер не смог извлечь» — не считаем успешным результатом
EXTRACTION_FAILURE_MARKERS = (
    "не удалось",
    "не удалось определить",
    "не удалось распознать",
    "к сожалению, не удалось",
)


def test_data_root() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def case_dir(case_name: str = CASE_2026_06_17) -> Path:
    return test_data_root() / case_name


def load_json(path: Path) -> Any:
    """Читает JSON с fallback utf-8 → cp1251 (экспорты с Windows)."""
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp1251"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return json.loads(raw.decode("utf-8", errors="replace"))


def load_result_parser(case_name: str = CASE_2026_06_17) -> dict:
    return load_json(case_dir(case_name) / "result_parser.json")


def load_generation_input(case_name: str = CASE_2026_06_17) -> dict | None:
    path = case_dir(case_name) / "generation_input.json"
    if not path.is_file():
        return None
    return load_json(path)


def missing_generation_fields(generation_input: dict | None) -> list[str]:
    """Список отсутствующих/пустых полей, нужных для генерации иска."""
    if generation_input is None:
        return ["generation_input.json (файл отсутствует)"]

    missing: list[str] = []
    for key in REQUIRED_GENERATION_FIELDS:
        if not str(generation_input.get(key, "")).strip():
            missing.append(key)

    plaintiff = generation_input.get("plaintiff_info") or {}
    for key in REQUIRED_PLAINTIFF_FIELDS:
        if not str(plaintiff.get(key, "")).strip():
            missing.append(f"plaintiff_info.{key}")

    lawsuit = generation_input.get("lawsuit_info") or {}
    if not str(lawsuit.get("service_type", "")).strip():
        missing.append("lawsuit_info.service_type")

    complects = generation_input.get("complects") or []
    if not complects:
        missing.append("complects")
    else:
        for i, complect in enumerate(complects):
            if complect.get("day_of_penalty") is None or str(complect.get("day_of_penalty")).strip() == "":
                missing.append(f"complects[{i}].day_of_penalty")
            if not str(complect.get("contract_type", "")).strip():
                missing.append(f"complects[{i}].contract_type")
            if not str(complect.get("contract_point", "")).strip():
                missing.append(f"complects[{i}].contract_point")

    return missing


def case_files(case_name: str = CASE_2026_06_17) -> dict[str, Path]:
    """Явные пути к входным и эталонным файлам кейса 2026-06-17."""
    root = case_dir(case_name)
    complect = root / "complect_1"
    return {
        "root": root,
        "excel": complect / "03.200306-_.XLSM",
        "contract_pdf": complect / "2._30_..pdf",
        "claim_pdf": complect / "26.12.25_08-00.pdf",
        "egrul_pdf": root / "ul-1077762468277-20260617160054.pdf",
        "result_parser": root / "result_parser.json",
        "generation_input": root / "generation_input.json",
        "golden_claim": root / "ИСК.docx",
        "golden_calculation": root / "расчёт к иску.docx",
    }


def normalize_quotes(text: str) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("«", '"')
        .replace("»", '"')
        .replace("“", '"')
        .replace("”", '"')
        .replace("„", '"')
        .replace("‟", '"')
    )


def normalize_name(text: str) -> str:
    return " ".join(normalize_quotes(text).upper().split())


def _norm_field(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def is_extraction_failure(value: Any) -> bool:
    text = _norm_field(value).lower()
    if not text or text in {"-", "none", "null"}:
        return True
    return any(marker in text for marker in EXTRACTION_FAILURE_MARKERS)


def extraction_vs_user_mismatches(
    result_parser: dict, generation_input: dict
) -> list[dict[str, str]]:
    """
    Сравнивает пересекающиеся поля: извлечённые (result_parser) и
    введённые пользователем (generation_input).

    Возвращает список расхождений:
    [{"field": "...", "extracted": "...", "user": "..."}, ...]
    """
    mismatches: list[dict[str, str]] = []
    parsed_complects = result_parser.get("table_parser_result") or []
    user_complects = generation_input.get("complects") or []

    if len(parsed_complects) != len(user_complects):
        mismatches.append(
            {
                "field": "complects.length",
                "extracted": str(len(parsed_complects)),
                "user": str(len(user_complects)),
            }
        )

    for i, (parsed, user) in enumerate(zip(parsed_complects, user_complects)):
        pairs = (
            (f"complects[{i}].contract_type", parsed[2], user.get("contract_type")),
            (f"complects[{i}].contract_point", parsed[3], user.get("contract_point")),
            (f"complects[{i}].day_of_penalty", parsed[4], user.get("day_of_penalty")),
        )
        for field, extracted, user_val in pairs:
            if _norm_field(extracted) != _norm_field(user_val):
                mismatches.append(
                    {
                        "field": field,
                        "extracted": _norm_field(extracted),
                        "user": _norm_field(user_val),
                    }
                )

        claims = parsed[6] if len(parsed) > 6 else []
        for j, claim in enumerate(claims):
            for key in ("claim_number", "claim_date"):
                val = claim.get(key) if isinstance(claim, dict) else None
                if is_extraction_failure(val):
                    mismatches.append(
                        {
                            "field": f"complects[{i}].claims[{j}].{key}",
                            "extracted": _norm_field(val),
                            "user": "(ожидалось распознанное значение)",
                        }
                    )

    defendant = (result_parser.get("results_of_name_parser") or {}).get(
        "defendant_info"
    ) or {}
    for key in ("full_name", "short_name", "address", "inn", "ogrn", "kpp"):
        if key in defendant and is_extraction_failure(defendant.get(key)):
            mismatches.append(
                {
                    "field": f"defendant_info.{key}",
                    "extracted": _norm_field(defendant.get(key)),
                    "user": "(ожидалось распознанное значение)",
                }
            )

    return mismatches


def format_extraction_mismatch(m: dict[str, str]) -> str:
    extracted = m["extracted"]
    if is_extraction_failure(extracted):
        return (
            f"{m['field']}: не удалось извлечь из документов "
            f"(получено {extracted!r}, ожидалось {m['user']!r})"
        )
    return (
        f"{m['field']}: извлечено={extracted!r}, "
        f"пользователь/ожидание={m['user']!r}"
    )


def warn_extraction_mismatches(
    result_parser: dict, generation_input: dict
) -> list[dict[str, str]]:
    """
    Сверяет извлечённые данные с generation_input.
    При расхождении пишет warning (тест не падает) и возвращает список mismatches.
    """
    mismatches = extraction_vs_user_mismatches(result_parser, generation_input)
    if mismatches:
        details = "; ".join(format_extraction_mismatch(m) for m in mismatches)
        warnings.warn(
            "Извлечённые данные не совпадают с эталоном пользователя "
            f"(generation_input): {details}",
            UserWarning,
            stacklevel=2,
        )
    return mismatches


def warn_field_extracted(field: str, value: Any, expected: Any) -> bool:
    """
    Сверяет поле с ожиданием. При заглушке/расхождении — warning.
    Возвращает True, если значение совпало с ожиданием.
    """
    if is_extraction_failure(value):
        warnings.warn(
            f"{field}: не удалось извлечь из документов "
            f"(получено {value!r}, ожидалось {expected!r})",
            UserWarning,
            stacklevel=2,
        )
        return False
    if _norm_field(value) != _norm_field(expected):
        warnings.warn(
            f"{field}: извлечено={value!r}, ожидалось={expected!r}",
            UserWarning,
            stacklevel=2,
        )
        return False
    return True
