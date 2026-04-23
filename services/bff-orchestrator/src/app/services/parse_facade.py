"""Parse pipeline: TableParser + PDF-заглушки V2 (без torch/docling в воркере)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

# Репозиторий: .../services/bff-orchestrator/src/app/services/parse_facade.py
_REPO_ROOT = Path(__file__).resolve().parents[5]
_V2_PYTHON = _REPO_ROOT / "LegalDocInspectorV2" / "python"
if _V2_PYTHON.is_dir() and str(_V2_PYTHON) not in sys.path:
    sys.path.insert(0, str(_V2_PYTHON))

from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser  # noqa: E402
from LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate import (  # noqa: E402
    parse_egrul_certificate,
)

from configs.config import AppConfig  # noqa: E402

from legaldoc_v2.parsers import ClaimParserStub, ContractParserStub  # noqa: E402


def _default_table_row(contract_number: str) -> tuple[Any, ...]:
    """Строка результата: кортеж из 7 элементов (form_helpers / calculate)."""
    return (
        {},
        contract_number,
        "unknown",
        "",
        "64",
        "",
        [{"claim_date": "", "claim_number": ""}],
    )


def _default_defendant_block(inn: str = "") -> dict[str, Any]:
    return {
        "inn": inn or "",
        "full_name": "",
        "short_name": "",
        "address": "",
        "kpp": "",
        "ogrn": "",
    }


def run_parse(
    folder: Path,
    application_date: str,
    complects_count: int,
    certificates_per_complect: list[int],
    config: AppConfig,
    *,
    ocr_engine_config_path: Path | None = None,
) -> dict:
    """
    application_date: ISO YYYY-MM-DD или DD.MM.YYYY → DD.MM.YYYY.
    certificates_per_complect: индекс 0 → комплект 1.

    Ошибки не пробрасываются: дефолтный JSON и список ``parse_warnings``.
    """
    _ = ocr_engine_config_path

    parse_warnings: list[str] = []
    table_parser = TableParser()
    claim_parser = ClaimParserStub()
    contract_parser = ContractParserStub()

    try:
        date_request = date.fromisoformat(application_date.strip()).strftime("%d.%m.%Y")
    except ValueError:
        parse_warnings.append(
            "Некорректная дата заявления «"
            f"{application_date}», подставлена дата сегодня."
        )
        date_request = date.today().strftime("%d.%m.%Y")

    folder.mkdir(parents=True, exist_ok=True)

    parsing_table_results: list[tuple[Any, ...]] = []
    defendant_inn = ""

    egrul_dir = folder / "egrul"
    egrul_dir.mkdir(parents=True, exist_ok=True)
    egrul_candidates = sorted(egrul_dir.glob("egrul.*"))
    if not egrul_candidates:
        parse_warnings.append(
            "Выписка ЕГРЮЛ не найдена (ожидался файл egrul.* в каталоге egrul)."
        )
        egrul_certificate_file_path: Path | None = None
    else:
        egrul_certificate_file_path = egrul_candidates[0]

    if complects_count < 1:
        parse_warnings.append(
            "Число комплектов меньше 1 — в результат добавлена пустая строка по умолчанию."
        )
        parsing_table_results.append(_default_table_row("0"))

    for complect_id in range(1, complects_count + 1):
        complect_folder = folder / f"complect_{complect_id}"
        complect_folder.mkdir(parents=True, exist_ok=True)

        contracts = sorted(complect_folder.glob("contract.*"))
        claims = sorted(complect_folder.glob("claim.*"))
        if not contracts or not claims:
            parse_warnings.append(
                f"Комплект {complect_id}: нет договора или претензии (PDF) — строка по умолчанию."
            )
            parsing_table_results.append(_default_table_row(str(complect_id)))
            continue

        contract_file_path = contracts[0]
        claim_file_path = claims[0]

        try:
            certificates_count = int(certificates_per_complect[complect_id - 1])
        except (IndexError, TypeError, ValueError):
            parse_warnings.append(
                f"Комплект {complect_id}: неверное число справок в метаданных — принято 0."
            )
            certificates_count = 0

        table_parser_results: list[dict[str, Any]] = []
        contract_number = str(complect_id)

        for claim_id in range(certificates_count):
            certificate_file_path = complect_folder / f"certificate_{claim_id}.xlsx"
            if not certificate_file_path.exists():
                alt = list(complect_folder.glob(f"certificate_{claim_id}.*"))
                if alt:
                    certificate_file_path = alt[0]
                else:
                    parse_warnings.append(
                        f"Комплект {complect_id}: не найдена справка {claim_id} — пропуск."
                    )
                    table_parser_results.append({})
                    continue

            try:
                table_parser.open(str(certificate_file_path))
                result = table_parser.parse()
                inn_raw = table_parser.parse_defendant_inn()
                cn_raw = table_parser.parse_contract_number()
                table_parser.close()
                table_parser_results.append(result)
                if inn_raw is not None and str(inn_raw).strip():
                    defendant_inn = str(inn_raw).strip()
                if cn_raw is not None and str(cn_raw).strip():
                    contract_number = str(cn_raw).strip()
            except Exception as e:
                msg = (
                    f"Комплект {complect_id}, справка {claim_id}: "
                    f"ошибка разбора Excel ({e})."
                )
                parse_warnings.append(msg)
                try:
                    table_parser.close()
                except Exception:
                    pass
                table_parser_results.append({})

        merged_table_result: dict[str, Any] = {}
        for table_result in table_parser_results:
            if isinstance(table_result, dict):
                merged_table_result.update(table_result)

        try:
            contract_type, contract_point, overdue_date, contract_text = (
                contract_parser.analyse_contract(contract_file_path, config)
            )
            claim_info = claim_parser.analyse_claim(claim_file_path)
        except Exception as e:
            parse_warnings.append(
                f"Комплект {complect_id}: ошибка разбора PDF ({e})."
            )
            contract_type, contract_point, overdue_date, contract_text = (
                "ТЭ",
                "",
                "18",
                "",
            )
            claim_info = [{"claim_date": "", "claim_number": ""}]

        parsing_table_results.append(
            (
                merged_table_result,
                contract_number,
                contract_type,
                contract_point,
                overdue_date,
                contract_text,
                claim_info,
            )
        )

    if not parsing_table_results:
        parse_warnings.append(
            "Нет ни одной строки результата таблицы — добавлена запись по умолчанию."
        )
        parsing_table_results.append(_default_table_row("0"))

    result_json: dict[str, Any] = {
        "table_parser_result": parsing_table_results,
        "results_of_name_parser": {
            "defendant_info": _default_defendant_block(defendant_inn),
        },
        "path_to_save": str(folder.resolve()),
        "application_date": date_request,
        "parse_warnings": parse_warnings,
    }

    di = result_json["results_of_name_parser"]["defendant_info"]
    di["inn"] = defendant_inn or di.get("inn", "")

    if egrul_certificate_file_path is not None:
        try:
            full_name, short_name, address, kpp, ogrn, _tc = parse_egrul_certificate(
                str(egrul_certificate_file_path)
            )
            if not short_name:
                short_name = full_name
            di["full_name"] = full_name.upper()
            di["short_name"] = short_name
            di["address"] = address
            di["kpp"] = kpp
            di["ogrn"] = ogrn
        except Exception as e:
            parse_warnings.append(f"Ошибка разбора выписки ЕГРЮЛ: {e}")

    return result_json
