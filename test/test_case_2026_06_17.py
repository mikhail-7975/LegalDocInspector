"""
Юнит- и интеграционные тесты на папку
test/data/documents_from_request_2026-06-17_160359.877789
"""

from __future__ import annotations

from pathlib import Path

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
from test.helpers.case_loader import (
    warn_extraction_mismatches,
    warn_field_extracted,
    normalize_name,
    normalize_quotes,
)
from test.helpers.docx_compare import assert_docx_contains, normalize_docx_text, extract_docx_text


# ---------------------------------------------------------------------------
# Excel (быстрый юнит)
# ---------------------------------------------------------------------------


def test_excel_parser_matches_result_json(case_2026_06_17_files, case_2026_06_17_result):
    expected_tuple = case_2026_06_17_result["table_parser_result"][0]
    expected_table = expected_tuple[0]
    expected_contract_number = expected_tuple[1]
    expected_inn = case_2026_06_17_result["results_of_name_parser"]["defendant_info"]["inn"]

    parser = TableParser()
    parser.open(str(case_2026_06_17_files["excel"]))
    try:
        table = parser.parse()
        contract_number = parser.parse_contract_number()
        inn = parser.parse_defendant_inn()
    finally:
        parser.close()

    assert table == expected_table
    assert contract_number == expected_contract_number
    assert str(inn) == str(expected_inn)
    assert "Октябрь 2025" in table
    assert table["Октябрь 2025"]["accrual"]["debt"] == 318284.81


# ---------------------------------------------------------------------------
# Калькулятор пени (данные из JSON + generation_input)
# ---------------------------------------------------------------------------


def test_penalty_calculator_matches_golden_totals(
    case_2026_06_17_result, require_generation_input
):
    gen = require_generation_input
    parsed = case_2026_06_17_result["table_parser_result"][0][0]
    complect = gen["complects"][0]

    calculated = calculate_penalty(
        parsed_data=parsed,
        day_of_penalty=complect["day_of_penalty"],
        company_type=gen["company_type"],
        end_date=gen["end_date"],
    )

    assert calculated["end_of_table1"]["money"] == "318 284,81"
    assert calculated["end_of_table2"]["money"] == "3 628,45"
    assert calculated["start_of_table"]["start"] == "21.11.2025"
    assert calculated["start_of_table"]["end"] == "25.01.2026"


# ---------------------------------------------------------------------------
# Извлечённые данные ↔ введённые пользователем (generation_input)
# ---------------------------------------------------------------------------


def test_extracted_matches_user_input(
    case_2026_06_17_result, require_generation_input
):
    """
    Сверяет result_parser.json с generation_input.json.
    Расхождения / заглушки «не удалось…» — warning, не fail.
    """
    warn_extraction_mismatches(case_2026_06_17_result, require_generation_input)


def test_user_input_applied_in_claim_data(
    case_2026_06_17_result, require_generation_input
):
    """В claim_data после расчёта должны оказаться значения из generation_input."""
    gen = require_generation_input
    parsed = case_2026_06_17_result["table_parser_result"][0]
    complect_ui = gen["complects"][0]

    calculated = calculate_penalty(
        parsed_data=parsed[0],
        day_of_penalty=complect_ui["day_of_penalty"],
        company_type=gen["company_type"],
        end_date=gen["end_date"],
    )
    calculated["contract_number"] = parsed[1]
    calculated["contract_type"] = complect_ui["contract_type"]
    calculated_sorted = _sort_calculator_result(calculated)

    claim_data = convert_data(
        calculated_data_list=[calculated_sorted],
        last_days_of_penalty=[complect_ui["day_of_penalty"]],
        contract_points=[complect_ui["contract_point"]],
        company_type=gen["company_type"],
        current_date=gen["end_date"],
    )
    claim_data["plaintiff_info"] = gen["plaintiff_info"]
    claim_data["lawsuit_info"] = {
        "cost": claim_data["table_info"]["cost_of_lawsuit"],
        "tax": str(calculate_state_duty(claim_data["table_info"]["cost_of_lawsuit"])),
        "service_type": gen["lawsuit_info"]["service_type"],
        "claims": [
            f"№ {c['claim_number']} от {c['claim_date']}" for c in parsed[6]
        ],
    }
    claim_data["responsitive_name"] = gen["responsitive_name"]

    assert claim_data["company_type"] == gen["company_type"]
    assert claim_data["plaintiff_info"] == gen["plaintiff_info"]
    assert claim_data["responsitive_name"] == gen["responsitive_name"]
    assert claim_data["lawsuit_info"]["service_type"] == gen["lawsuit_info"]["service_type"]
    assert calculated["contract_type"] == complect_ui["contract_type"]

    contract_number = parsed[1]
    table_row = claim_data["table_info"][contract_number]
    assert table_row["contract_point"] == complect_ui["contract_point"]
    assert str(complect_ui["day_of_penalty"]) in table_row["last_day"]
    assert claim_data["current_date"] == "2026-01-25"


# ---------------------------------------------------------------------------
# ЕГРЮЛ / PDF — integration (docling)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_egrul_parser_matches_result_json(case_2026_06_17_files, case_2026_06_17_result):
    expected = case_2026_06_17_result["results_of_name_parser"]["defendant_info"]
    full_name, short_name, address, kpp, ogrn, _text = parse_egrul_certificate(
        case_2026_06_17_files["egrul_pdf"]
    )

    assert normalize_name(full_name) == normalize_name(expected["full_name"])
    assert normalize_name(short_name) == normalize_name(expected["short_name"])
    assert normalize_quotes(address).upper().replace(" ", "") == normalize_quotes(
        expected["address"]
    ).upper().replace(" ", "")
    assert str(kpp) == str(expected["kpp"])
    assert str(ogrn) == str(expected["ogrn"])


@pytest.mark.integration
@pytest.mark.slow
def test_claim_parser_matches_result_json(
    case_2026_06_17_files, case_2026_06_17_result, claim_parser
):
    expected = case_2026_06_17_result["table_parser_result"][0][6]
    claims = claim_parser.analyse_claim(case_2026_06_17_files["claim_pdf"])
    assert len(claims) == len(expected)
    for i, (got, exp) in enumerate(zip(claims, expected)):
        warn_field_extracted(
            f"claims[{i}].claim_number", got["claim_number"], exp["claim_number"]
        )
        warn_field_extracted(
            f"claims[{i}].claim_date", got["claim_date"], exp["claim_date"]
        )


@pytest.mark.integration
@pytest.mark.slow
def test_contract_parser_matches_user_input(
    case_2026_06_17_files,
    require_generation_input,
    contract_parser,
    app_config,
):
    """
    Тип/пункт/день договора сверяются с generation_input.
    Заглушки / расхождения — warning, не fail.
    """
    expected = require_generation_input["complects"][0]
    contract_type, contract_point, overdue_day, _contract_text = (
        contract_parser.analyse_contract(
            case_2026_06_17_files["contract_pdf"], app_config
        )
    )
    warn_field_extracted("contract_type", contract_type, expected["contract_type"])
    warn_field_extracted("contract_point", contract_point, expected["contract_point"])
    warn_field_extracted("day_of_penalty", overdue_day, expected["day_of_penalty"])


# ---------------------------------------------------------------------------
# Интеграция: parse → calculate → generate ↔ эталонные docx
# ---------------------------------------------------------------------------


def _sort_calculator_result(data: dict) -> dict:
    """Локальная копия порядка ключей из backend/routes.sort_data_structure."""
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


def _require_templates(app_config) -> tuple[str, str]:
    claim_tpl = Path(app_config.claim_template_path)
    calc_tpl = Path(app_config.calculation_claim_template_path)
    missing = [str(p) for p in (claim_tpl, calc_tpl) if not p.is_file()]
    if missing:
        pytest.skip("Нет шаблонов для генерации: " + ", ".join(missing))
    return str(claim_tpl), str(calc_tpl)


@pytest.mark.integration
@pytest.mark.slow
def test_pipeline_parse_calculate_generate_matches_golden(
    case_2026_06_17_files,
    case_2026_06_17_result,
    require_generation_input,
    claim_parser,
    contract_parser,
    app_config,
    tmp_path,
):
    gen = require_generation_input
    claim_tpl, calc_tpl = _require_templates(app_config)
    expected = case_2026_06_17_result
    expected_tuple = expected["table_parser_result"][0]

    # --- parse (как /parse) ---
    table_parser = TableParser()
    table_parser.open(str(case_2026_06_17_files["excel"]))
    try:
        table = table_parser.parse()
        contract_number = table_parser.parse_contract_number()
        defendant_inn = table_parser.parse_defendant_inn()
    finally:
        table_parser.close()

    contract_type, contract_point, overdue_day, contract_text = (
        contract_parser.analyse_contract(
            case_2026_06_17_files["contract_pdf"], app_config
        )
    )
    claim_info = claim_parser.analyse_claim(case_2026_06_17_files["claim_pdf"])
    full_name, short_name, address, kpp, ogrn, _ = parse_egrul_certificate(
        case_2026_06_17_files["egrul_pdf"]
    )
    if not short_name:
        short_name = full_name

    parsed_complect = [
        table,
        contract_number,
        contract_type,
        contract_point,
        overdue_day,
        contract_text,
        claim_info,
    ]

    # Excel / номер договора / претензия — как в result_parser.json
    assert parsed_complect[0] == expected_tuple[0]
    assert parsed_complect[1] == expected_tuple[1]
    assert parsed_complect[6] == expected_tuple[6]

    # Договор: сверка с generation_input — warning при расхождении;
    # для расчёта/генерации всегда берём значения пользователя.
    complect_ui = gen["complects"][0]
    warn_field_extracted("contract_type", contract_type, complect_ui["contract_type"])
    warn_field_extracted("contract_point", contract_point, complect_ui["contract_point"])
    warn_field_extracted("day_of_penalty", overdue_day, complect_ui["day_of_penalty"])

    expected_def = expected["results_of_name_parser"]["defendant_info"]
    assert str(defendant_inn) == str(expected_def["inn"])
    assert normalize_name(full_name) == normalize_name(expected_def["full_name"])
    assert normalize_name(short_name) == normalize_name(expected_def["short_name"])
    assert str(kpp) == str(expected_def["kpp"])
    assert str(ogrn) == str(expected_def["ogrn"])

    # --- calculate (overrides из generation_input) ---
    calculated = calculate_penalty(
        parsed_data=table,
        day_of_penalty=complect_ui["day_of_penalty"],
        company_type=gen["company_type"],
        end_date=gen["end_date"],
    )
    calculated["contract_number"] = contract_number
    calculated["contract_type"] = complect_ui["contract_type"]
    calculated_sorted = _sort_calculator_result(calculated)

    claim_data = convert_data(
        calculated_data_list=[calculated_sorted],
        last_days_of_penalty=[complect_ui["day_of_penalty"]],
        contract_points=[complect_ui["contract_point"]],
        company_type=gen["company_type"],
        current_date=gen["end_date"],
    )
    claim_data["plaintiff_info"] = gen["plaintiff_info"]
    claim_data["defendant_info"] = {
        "inn": str(defendant_inn),
        "full_name": full_name.upper(),
        "short_name": short_name,
        "addres": address,
        "ogrn": ogrn,
        "kpp": kpp,
    }
    cost = claim_data["table_info"]["cost_of_lawsuit"]
    tax = str(calculate_state_duty(cost))
    claims_for_lawsuit = [
        f"№ {item['claim_number']} от {item['claim_date']}" for item in claim_info
    ]
    claim_data["lawsuit_info"] = {
        "cost": cost,
        "tax": tax,
        "service_type": gen["lawsuit_info"]["service_type"],
        "claims": claims_for_lawsuit,
    }
    claim_data["responsitive_name"] = gen["responsitive_name"]

    # Пользовательские / извлечённые значения должны попасть в claim_data
    assert claim_data["company_type"] == gen["company_type"]
    assert claim_data["plaintiff_info"]["inn"] == gen["plaintiff_info"]["inn"]
    assert claim_data["plaintiff_info"]["full_name"] == gen["plaintiff_info"]["full_name"]
    assert claim_data["lawsuit_info"]["service_type"] == gen["lawsuit_info"]["service_type"]
    assert claim_data["responsitive_name"] == gen["responsitive_name"]
    assert calculated["contract_type"] == complect_ui["contract_type"]
    assert claim_data["table_info"][contract_number]["contract_point"] == complect_ui[
        "contract_point"
    ]
    assert str(complect_ui["day_of_penalty"]) in claim_data["table_info"][contract_number][
        "last_day"
    ]

    assert calculated["end_of_table1"]["money"] == "318 284,81"
    assert calculated["end_of_table2"]["money"] == "3 628,45"
    assert cost == "321 913,26"
    assert tax == "21 096,00"

    # --- generate ---
    out_claim = tmp_path / "ИСК.docx"
    out_calc = tmp_path / "расчёт к иску.docx"

    ClaimGenerator().make_instance(
        config=claim_data,
        template_filename=claim_tpl,
        output_filename=str(out_claim),
    )
    CalculationClaimGenerator().make_instance(
        config=[calculated_sorted],
        config2=claim_data,
        template_filename=calc_tpl,
        output_filename=str(out_calc),
    )

    claim_anchors = (
        "МОЭК",
        "АСБЕСТ",
        "03.200306-ТЭ",
        "318 284,81",
        "3 628,45",
        "321 913,26",
        "21 096,00",
        "21.11.2025",
        "25.01.2026",
        "595466",
        "Самошкина",
    )
    assert_docx_contains(out_claim, *claim_anchors)
    assert_docx_contains(
        out_calc,
        "318 284,81",
        "3 628,45",
        "21.11.2025",
        "25.01.2026",
        "03.200306-ТЭ",
    )

    golden_claim_text = normalize_docx_text(
        extract_docx_text(case_2026_06_17_files["golden_claim"])
    )
    generated_claim_text = normalize_docx_text(extract_docx_text(out_claim))
    for needle in claim_anchors:
        assert needle in golden_claim_text
        assert needle in generated_claim_text

    # Содержимое эталона и сгенерированного иска должно совпадать
    # (uuid в claim_data в текст документа не попадает).
    assert generated_claim_text == golden_claim_text

    golden_calc_text = normalize_docx_text(
        extract_docx_text(case_2026_06_17_files["golden_calculation"])
    )
    generated_calc_text = normalize_docx_text(extract_docx_text(out_calc))
    assert generated_calc_text == golden_calc_text
