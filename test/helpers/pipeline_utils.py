"""Общие шаги parse → calculate → generate для тестов documents_from_request_*."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import (
    calculate_penalty,
)
from LegalDocInspector.legal_doc_inspector.doc_creator.calculation_claim_generator import (
    CalculationClaimGenerator,
)
from LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator
from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser
from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import calculate_state_duty
from LegalDocInspector.legal_doc_inspector.utils.calculator_adapter import convert_data
from LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate import (
    parse_egrul_certificate,
)
from test.helpers.case_loader import normalize_name, warn_field_extracted
from test.helpers.docx_compare import (
    assert_docx_contains,
    extract_docx_text,
    normalize_docx_text,
)


def sort_calculator_result(data: dict) -> dict:
    """Порядок ключей как в backend/routes.sort_data_structure."""
    sorted_data: dict = {}
    if "start_of_table" in data:
        sorted_data["start_of_table"] = data["start_of_table"]

    month_order = {
        "Январь": 1,
        "Февраль": 2,
        "Март": 3,
        "Апрель": 4,
        "Май": 5,
        "Июнь": 6,
        "Июль": 7,
        "Август": 8,
        "Сентябрь": 9,
        "Октябрь": 10,
        "Ноябрь": 11,
        "Декабрь": 12,
    }
    months = []
    for key in data:
        if isinstance(key, str) and len(key.split()) == 2:
            month_name, year_str = key.split()
            try:
                year = int(year_str)
            except ValueError:
                continue
            months.append((key, year, month_name))
    months.sort(key=lambda item: (item[1], month_order.get(item[2], 99)))
    for key, _, _ in months:
        sorted_data[key] = data[key]

    for key in ("end_of_table1", "end_of_table2", "debt_info", "contract_number", "contract_type"):
        if key in data:
            sorted_data[key] = data[key]
    return sorted_data


def require_templates(app_config) -> tuple[str, str]:
    claim_tpl = Path(app_config.claim_template_path)
    calc_tpl = Path(app_config.calculation_claim_template_path)
    missing = [str(p) for p in (claim_tpl, calc_tpl) if not p.is_file()]
    if missing:
        pytest.skip("Нет шаблонов для генерации: " + ", ".join(missing))
    return str(claim_tpl), str(calc_tpl)


def parse_excel(excel_path: Path) -> tuple[dict, str, str | None]:
    parser = TableParser()
    parser.open(str(excel_path))
    try:
        table = parser.parse()
        contract_number = parser.parse_contract_number()
        inn = parser.parse_defendant_inn()
    finally:
        parser.close()
    return table, contract_number, None if inn is None else str(inn)


def build_claim_data_for_case(
    *,
    result_parser: dict,
    generation_input: dict,
    files: dict[str, Any],
    claim_parser,
    contract_parser,
    app_config,
) -> tuple[dict, list[dict]]:
    """
    Парсит входы, считает пени с overrides из generation_input,
    возвращает (claim_data, calculator_list_sorted).
    """
    gen = generation_input
    expected_tuples = result_parser["table_parser_result"]
    complects_meta = files["complects"]
    if len(complects_meta) != len(expected_tuples):
        pytest.skip(
            f"Число complect_* ({len(complects_meta)}) != "
            f"table_parser_result ({len(expected_tuples)})"
        )
    if len(gen.get("complects") or []) != len(expected_tuples):
        pytest.skip("generation_input.complects не совпадает с числом комплектов")

    calculated_list: list[dict] = []
    days: list[Any] = []
    points: list[str] = []
    all_claims: list[dict] = []
    defendant_inn = None
    last_egrul = None

    for i, (meta, expected_tuple) in enumerate(zip(complects_meta, expected_tuples)):
        if meta["excel"] is None:
            pytest.skip(f"Нет Excel в {meta['dir']}")
        table, contract_number, inn = parse_excel(meta["excel"])
        assert table == expected_tuple[0]
        assert contract_number == expected_tuple[1]
        if inn is not None:
            defendant_inn = inn

        ui = gen["complects"][i]
        if meta["contract_pdf"] is not None:
            ctype, cpoint, overdue_day, _ = contract_parser.analyse_contract(
                meta["contract_pdf"], app_config
            )
            warn_field_extracted(
                f"complects[{i}].contract_type", ctype, ui["contract_type"]
            )
            warn_field_extracted(
                f"complects[{i}].contract_point", cpoint, ui["contract_point"]
            )
            warn_field_extracted(
                f"complects[{i}].day_of_penalty", overdue_day, ui["day_of_penalty"]
            )

        if meta["claim_pdf"] is not None:
            claims = claim_parser.analyse_claim(meta["claim_pdf"])
            assert len(claims) == len(expected_tuple[6])
            for j, (got, exp) in enumerate(zip(claims, expected_tuple[6])):
                warn_field_extracted(
                    f"complects[{i}].claims[{j}].claim_number",
                    got["claim_number"],
                    exp["claim_number"],
                )
                warn_field_extracted(
                    f"complects[{i}].claims[{j}].claim_date",
                    got["claim_date"],
                    exp["claim_date"],
                )
            all_claims.extend(claims)
        else:
            all_claims.extend(expected_tuple[6])

        calculated = calculate_penalty(
            parsed_data=table,
            day_of_penalty=ui["day_of_penalty"],
            company_type=gen["company_type"],
            end_date=gen["end_date"],
        )
        calculated["contract_number"] = contract_number
        calculated["contract_type"] = ui["contract_type"]
        calculated_list.append(sort_calculator_result(calculated))
        days.append(ui["day_of_penalty"])
        points.append(ui["contract_point"])

    if files.get("egrul_pdf") is not None:
        full_name, short_name, address, kpp, ogrn, _ = parse_egrul_certificate(
            files["egrul_pdf"]
        )
        if not short_name:
            short_name = full_name
        last_egrul = (full_name, short_name, address, kpp, ogrn)
        expected_def = result_parser["results_of_name_parser"]["defendant_info"]
        assert normalize_name(full_name) == normalize_name(expected_def["full_name"])
        assert str(ogrn) == str(expected_def["ogrn"])
        if defendant_inn is None:
            defendant_inn = str(expected_def.get("inn") or "")
    else:
        expected_def = result_parser["results_of_name_parser"]["defendant_info"]
        last_egrul = (
            expected_def.get("full_name") or "",
            expected_def.get("short_name") or expected_def.get("full_name") or "",
            expected_def.get("address") or "",
            expected_def.get("kpp") or "",
            expected_def.get("ogrn") or "",
        )
        if defendant_inn is None:
            defendant_inn = str(expected_def.get("inn") or "")

    claim_data = convert_data(
        calculated_data_list=calculated_list,
        last_days_of_penalty=days,
        contract_points=points,
        company_type=gen["company_type"],
        current_date=gen["end_date"],
    )
    full_name, short_name, address, kpp, ogrn = last_egrul
    claim_data["plaintiff_info"] = gen["plaintiff_info"]
    claim_data["defendant_info"] = {
        "inn": str(defendant_inn),
        "full_name": str(full_name).upper(),
        "short_name": short_name,
        "addres": address,
        "ogrn": ogrn,
        "kpp": kpp,
    }
    cost = claim_data["table_info"]["cost_of_lawsuit"]
    tax = str(calculate_state_duty(cost))
    claim_data["lawsuit_info"] = {
        "cost": cost,
        "tax": tax,
        "service_type": gen["lawsuit_info"]["service_type"],
        "claims": [
            f"№ {c['claim_number']} от {c['claim_date']}" for c in all_claims
        ],
    }
    claim_data["responsitive_name"] = gen["responsitive_name"]
    return claim_data, calculated_list


def generate_and_compare_golden(
    *,
    claim_data: dict,
    calculator_list: list[dict],
    app_config,
    files: dict[str, Any],
    tmp_path: Path,
    extra_claim_anchors: tuple[str, ...] = (),
) -> None:
    claim_tpl, calc_tpl = require_templates(app_config)
    golden_claim = files["golden_claim"]
    golden_calc = files["golden_calculation"]
    if not golden_claim.is_file() or not golden_calc.is_file():
        pytest.skip("Нет эталонных ИСК.docx / расчёт к иску.docx")

    out_claim = tmp_path / "ИСК.docx"
    out_calc = tmp_path / "расчёт к иску.docx"

    ClaimGenerator().make_instance(
        config=claim_data,
        template_filename=claim_tpl,
        output_filename=str(out_claim),
    )
    CalculationClaimGenerator().make_instance(
        config=calculator_list,
        config2=claim_data,
        template_filename=calc_tpl,
        output_filename=str(out_calc),
    )

    cost = claim_data["lawsuit_info"]["cost"]
    tax = claim_data["lawsuit_info"]["tax"]
    anchors = (
        "МОЭК",
        str(cost),
        str(tax),
        gen_responsible_anchor(claim_data),
        *extra_claim_anchors,
    )
    # якоря, которые точно должны быть в обоих эталоне и генерации
    for needle in anchors:
        if needle:
            assert_docx_contains(out_claim, needle)

    golden_claim_text = normalize_docx_text(extract_docx_text(golden_claim))
    generated_claim_text = normalize_docx_text(extract_docx_text(out_claim))
    assert generated_claim_text == golden_claim_text

    golden_calc_text = normalize_docx_text(extract_docx_text(golden_calc))
    generated_calc_text = normalize_docx_text(extract_docx_text(out_calc))
    assert generated_calc_text == golden_calc_text


def gen_responsible_anchor(claim_data: dict) -> str:
    name = claim_data.get("responsitive_name") or ""
    return name.split()[0] if name else ""
