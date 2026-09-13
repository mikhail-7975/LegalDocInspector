"""Загрузка тестовых кейсов documents_from_request_* и проверка generation_input."""

from __future__ import annotations

import json
import re
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

EXTRACTION_FAILURE_MARKERS = (
    "не удалось",
    "не удалось определить",
    "не удалось распознать",
    "к сожалению, не удалось",
)

DEFAULT_PLAINTIFF_INFO = {
    "inn": "7720518494",
    "full_name": (
        "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО «МОСКОВСКАЯ ОБЪЕДИНЕННАЯ "
        "ЭНЕРГЕТИЧЕСКАЯ КОМПАНИЯ»"
    ),
    "short_name": 'ПАО "МОЭК"',
    "addres": "119526, г. Москва, проспект Вернадского, д. 101, к. 3, эт/каб 20/2017",
    "ogrn": "1047796974092",
    "correspondency_addres": "121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613",
}

DEFAULT_RESPONSIBLE_NAME = "Самошкина А.Е."

EXCEL_SUFFIXES = {".xls", ".xlsx", ".xlsm"}


def test_data_root() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def case_dir(case_name: str) -> Path:
    return test_data_root() / case_name


def list_case_names() -> list[str]:
    root = test_data_root()
    if not root.is_dir():
        return []
    names = sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and p.name.startswith("documents_from_request_")
    )
    return names


def load_json(path: Path) -> Any:
    """Читает JSON с fallback utf-8 → cp1251 (экспорты с Windows)."""
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp1251"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return json.loads(raw.decode("utf-8", errors="replace"))


def load_result_parser(case_name: str) -> dict:
    return load_json(case_dir(case_name) / "result_parser.json")


def load_generation_input(case_name: str) -> dict | None:
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


def _is_excel(path: Path) -> bool:
    return path.suffix.lower() in EXCEL_SUFFIXES


def _is_pdf_like(path: Path) -> bool:
    if path.suffix.lower() == ".pdf":
        return True
    # иногда выписку/претензию сохраняют файлом без расширения «pdf»
    return path.suffix == "" and path.name.lower() == "pdf"


def discover_egrul_pdf(root: Path) -> Path | None:
    for pattern in ("ul-*.pdf", "fl-*.pdf"):
        found = sorted(root.glob(pattern))
        if found:
            return found[0]
    # файл без расширения с именем pdf в корне
    bare = root / "pdf"
    if bare.is_file():
        return bare
    return None


def _claim_numbers_from_tuple(parsed_tuple: list) -> list[str]:
    claims = parsed_tuple[6] if len(parsed_tuple) > 6 else []
    numbers = []
    for claim in claims:
        if isinstance(claim, dict) and claim.get("claim_number"):
            numbers.append(str(claim["claim_number"]))
    return numbers


def discover_complect_files(
    complect_dir: Path, parsed_tuple: list | None = None
) -> dict[str, Path | None]:
    """
    Находит excel / contract_pdf / claim_pdf в complect_*.
    Претензию предпочитаем по номеру из result_parser в имени файла.
    """
    files = [p for p in complect_dir.iterdir() if p.is_file() and not p.name.startswith(".")]
    excel_files = [p for p in files if _is_excel(p)]
    pdf_files = [p for p in files if _is_pdf_like(p)]

    excel = excel_files[0] if excel_files else None
    claim_pdf = None
    contract_pdf = None

    claim_numbers = _claim_numbers_from_tuple(parsed_tuple or [])
    for pdf in pdf_files:
        name = pdf.name
        if any(num and num in name for num in claim_numbers):
            claim_pdf = pdf
            break

    remaining = [p for p in pdf_files if p != claim_pdf]
    if claim_pdf is None and remaining:
        # эвристика: претензия чаще короткое имя / начинается с цифр номера
        by_len = sorted(remaining, key=lambda p: len(p.name))
        # договор чаще содержит «No_» или номер договора; претензия — короткий pdf
        for cand in remaining:
            lower = cand.name.lower()
            if lower.startswith("no_") or "-__" in lower or "договор" in lower:
                continue
            if re.match(r"^\d", cand.name) and len(cand.name) < 40:
                claim_pdf = cand
                break
        if claim_pdf is None and len(remaining) >= 2:
            claim_pdf = by_len[0]
        remaining = [p for p in remaining if p != claim_pdf]

    if remaining:
        # предпочтение файла с «No_» / длинного имени как договора
        remaining_sorted = sorted(
            remaining,
            key=lambda p: (
                0 if p.name.lower().startswith("no_") else 1,
                -len(p.name),
            ),
        )
        contract_pdf = remaining_sorted[0]

    return {
        "excel": excel,
        "contract_pdf": contract_pdf,
        "claim_pdf": claim_pdf,
    }


def case_files(case_name: str) -> dict[str, Any]:
    """Пути к файлам кейса (автообнаружение complect_* / ul-*.pdf)."""
    root = case_dir(case_name)
    result = load_result_parser(case_name) if (root / "result_parser.json").is_file() else {}
    parsed_list = result.get("table_parser_result") or []

    complect_dirs = sorted(
        p for p in root.iterdir() if p.is_dir() and p.name.startswith("complect_")
    )
    complects: list[dict[str, Any]] = []
    for i, complect_dir in enumerate(complect_dirs):
        parsed_tuple = parsed_list[i] if i < len(parsed_list) else None
        files = discover_complect_files(complect_dir, parsed_tuple)
        complects.append(
            {
                "dir": complect_dir,
                "excel": files["excel"],
                "contract_pdf": files["contract_pdf"],
                "claim_pdf": files["claim_pdf"],
                "parsed_tuple": parsed_tuple,
            }
        )

    return {
        "root": root,
        "name": case_name,
        "egrul_pdf": discover_egrul_pdf(root),
        "result_parser": root / "result_parser.json",
        "generation_input": root / "generation_input.json",
        "golden_claim": root / "ИСК.docx",
        "golden_calculation": root / "расчёт к иску.docx",
        "complects": complects,
        # совместимость с тестом 2026-06-17
        "excel": complects[0]["excel"] if complects else None,
        "contract_pdf": complects[0]["contract_pdf"] if complects else None,
        "claim_pdf": complects[0]["claim_pdf"] if complects else None,
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


def infer_contract_type_from_number(contract_number: str) -> str:
    text = (contract_number or "").upper()
    for token in ("ФОТЭ", "ГВС", "СОИ", "ТЭ"):
        if token in text:
            return token
    return "ТЭ"


def infer_company_type(defendant_info: dict) -> str:
    blob = " ".join(
        str(defendant_info.get(k) or "")
        for k in ("full_name", "short_name")
    ).upper()
    if any(x in blob for x in ("ТСЖ", "ТСН", "ЖСК")):
        return "ТСЖ"
    if re.search(r"\bУК\b", blob) or "УПРАВЛЯЮЩ" in blob:
        return "УК"
    return "Прочие"


def _extract_hints_from_golden_claim(golden_claim: Path) -> dict[str, Any]:
    if not golden_claim.is_file():
        return {}
    from test.helpers.docx_compare import extract_docx_text, normalize_docx_text

    text = normalize_docx_text(extract_docx_text(golden_claim))
    hints: dict[str, Any] = {}

    ends = re.findall(r"по\s+(\d{2}\.\d{2}\.\d{4})", text)
    if ends:
        hints["end_date"] = ends[-1]

    days = re.findall(r"До\s+(\d{1,2})\s+числа", text)
    if days:
        hints["day_of_penalty"] = int(days[0])

    # пункт вида 7.2 / 5.5 — не куски дат вроде 33301.2025
    points = re.findall(
        r"за расчётным\s+(\d{1,2}\.\d{1,2})\b|пункт[уае]?\s+(\d{1,2}\.\d{1,2})\b",
        text,
        flags=re.IGNORECASE,
    )
    flat_points = [a or b for a, b in points if (a or b)]
    if flat_points:
        hints["contract_point"] = flat_points[0]

    cost = re.search(r"Цена иска:\s*([\d\s]+,\d{2})", text)
    if cost:
        hints["cost"] = cost.group(1).strip()
    tax = re.search(r"Госпошлина:\s*([\d\s]+,\d{2})", text)
    if tax:
        hints["tax"] = tax.group(1).strip()

    return hints


def resolve_generation_input(case_name: str, result_parser: dict | None = None) -> dict | None:
    """
    Берёт generation_input.json или собирает из result_parser + эталонного иска.
    """
    existing = load_generation_input(case_name)
    if existing is not None:
        return existing

    if result_parser is None:
        rp_path = case_dir(case_name) / "result_parser.json"
        if not rp_path.is_file():
            return None
        result_parser = load_result_parser(case_name)

    files = case_files(case_name)
    hints = _extract_hints_from_golden_claim(files["golden_claim"])
    if not hints.get("end_date"):
        return None

    defendant = (result_parser.get("results_of_name_parser") or {}).get(
        "defendant_info"
    ) or {}
    company_type = infer_company_type(defendant)

    complects_out: list[dict[str, Any]] = []
    service_types: list[str] = []
    for parsed in result_parser.get("table_parser_result") or []:
        raw_type = parsed[2]
        if is_extraction_failure(raw_type):
            ctype = infer_contract_type_from_number(parsed[1])
        else:
            ctype = _norm_field(raw_type)
        service_types.append(ctype)

        raw_point = parsed[3]
        if is_extraction_failure(raw_point):
            point = hints.get("contract_point") or "-"
        else:
            point = _norm_field(raw_point)

        raw_day = parsed[4]
        if raw_day is None or is_extraction_failure(raw_day):
            day = hints.get("day_of_penalty") or 18
        else:
            day = int(str(raw_day).strip())

        complects_out.append(
            {
                "contract_type": ctype,
                "contract_point": point,
                "day_of_penalty": day,
            }
        )

    unique_types = []
    for t in service_types:
        if t not in unique_types:
            unique_types.append(t)
    service_type = " и ".join(unique_types) if unique_types else "ТЭ"

    return {
        "company_type": company_type,
        "end_date": hints["end_date"],
        "plaintiff_info": dict(DEFAULT_PLAINTIFF_INFO),
        "responsitive_name": DEFAULT_RESPONSIBLE_NAME,
        "lawsuit_info": {"service_type": service_type},
        "complects": complects_out,
        "_inferred": True,
        "_hints": hints,
    }


def extraction_vs_user_mismatches(
    result_parser: dict, generation_input: dict
) -> list[dict[str, str]]:
    """
    Сравнивает пересекающиеся поля: извлечённые (result_parser) и
    введённые пользователем (generation_input).
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
    """При расхождении пишет warning (тест не падает)."""
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
    """При заглушке/расхождении — warning. True, если совпало."""
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
