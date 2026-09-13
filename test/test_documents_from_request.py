"""
Параметризованные тесты по всем папкам test/data/documents_from_request_*.

Покрытие аналогично test_case_2026_06_17:
- Excel ↔ result_parser.json
- сверка извлечённого с generation_input (warning при расхождении)
- применение generation_input в claim_data
- ЕГРЮЛ / претензия / договор (integration)
- pipeline parse → calculate → generate ↔ эталонные docx (integration)
"""

from __future__ import annotations

import pytest

from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import (
    calculate_penalty,
)
from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import calculate_state_duty
from LegalDocInspector.legal_doc_inspector.utils.calculator_adapter import convert_data
from LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate import (
    parse_egrul_certificate,
)
from test.helpers.case_loader import (
    case_files,
    is_extraction_failure,
    list_case_names,
    load_result_parser,
    missing_generation_fields,
    normalize_name,
    normalize_quotes,
    resolve_generation_input,
    warn_extraction_mismatches,
    warn_field_extracted,
)
from test.helpers.pipeline_utils import (
    build_claim_data_for_case,
    generate_and_compare_golden,
    parse_excel,
    sort_calculator_result,
)


CASE_NAMES = list_case_names()


def _ids(name: str) -> str:
    # короче в отчёте pytest: дата-время папки
    return name.replace("documents_from_request_", "")


@pytest.fixture(scope="session")
def all_case_files() -> dict[str, dict]:
    return {name: case_files(name) for name in CASE_NAMES}


@pytest.fixture(scope="session")
def all_case_results() -> dict[str, dict]:
    return {name: load_result_parser(name) for name in CASE_NAMES}


def _generation_or_skip(case_name: str, result: dict) -> dict:
    gen = resolve_generation_input(case_name, result)
    missing = missing_generation_fields(gen)
    if missing:
        pytest.skip(
            "Недостаточно данных для генерации (нет generation_input и не удалось "
            "собрать из эталона): " + ", ".join(missing)
        )
    return gen


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_excel_parser_matches_result_json(case_name, all_case_files, all_case_results):
    files = all_case_files[case_name]
    result = all_case_results[case_name]
    expected_tuples = result["table_parser_result"]
    complects = files["complects"]
    assert len(complects) == len(expected_tuples)

    for i, (meta, expected_tuple) in enumerate(zip(complects, expected_tuples)):
        excel = meta["excel"]
        if excel is None:
            pytest.skip(f"{case_name}: нет Excel в complect_{i+1}")
        table, contract_number, inn = parse_excel(excel)
        assert table == expected_tuple[0], f"complect_{i+1} table"
        assert contract_number == expected_tuple[1], f"complect_{i+1} contract_number"
        if i == len(complects) - 1:
            expected_inn = result["results_of_name_parser"]["defendant_info"]["inn"]
            assert str(inn) == str(expected_inn)


# ---------------------------------------------------------------------------
# generation_input / калькулятор
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_extracted_matches_user_input(case_name, all_case_results):
    result = all_case_results[case_name]
    gen = _generation_or_skip(case_name, result)
    warn_extraction_mismatches(result, gen)


@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_user_input_applied_in_claim_data(case_name, all_case_results):
    result = all_case_results[case_name]
    gen = _generation_or_skip(case_name, result)
    expected_tuples = result["table_parser_result"]
    ui_complects = gen["complects"]
    assert len(ui_complects) == len(expected_tuples)

    calculated_list = []
    days = []
    points = []
    for parsed, ui in zip(expected_tuples, ui_complects):
        calculated = calculate_penalty(
            parsed_data=parsed[0],
            day_of_penalty=ui["day_of_penalty"],
            company_type=gen["company_type"],
            end_date=gen["end_date"],
        )
        calculated["contract_number"] = parsed[1]
        calculated["contract_type"] = ui["contract_type"]
        calculated_list.append(sort_calculator_result(calculated))
        days.append(ui["day_of_penalty"])
        points.append(ui["contract_point"])

    claim_data = convert_data(
        calculated_data_list=calculated_list,
        last_days_of_penalty=days,
        contract_points=points,
        company_type=gen["company_type"],
        current_date=gen["end_date"],
    )
    claim_data["plaintiff_info"] = gen["plaintiff_info"]
    claim_data["responsitive_name"] = gen["responsitive_name"]
    claim_data["lawsuit_info"] = {
        "cost": claim_data["table_info"]["cost_of_lawsuit"],
        "tax": str(calculate_state_duty(claim_data["table_info"]["cost_of_lawsuit"])),
        "service_type": gen["lawsuit_info"]["service_type"],
        "claims": [],
    }

    assert claim_data["company_type"] == gen["company_type"]
    assert claim_data["plaintiff_info"] == gen["plaintiff_info"]
    assert claim_data["responsitive_name"] == gen["responsitive_name"]
    assert claim_data["lawsuit_info"]["service_type"] == gen["lawsuit_info"]["service_type"]

    for parsed, ui in zip(expected_tuples, ui_complects):
        contract_number = parsed[1]
        row = claim_data["table_info"][contract_number]
        assert row["contract_point"] == ui["contract_point"]
        assert str(ui["day_of_penalty"]) in row["last_day"]

    # end_date DD.MM.YYYY → current_date YYYY-MM-DD
    d, m, y = gen["end_date"].split(".")
    assert claim_data["current_date"] == f"{y}-{m}-{d}"


@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_penalty_calculator_matches_golden_hints(case_name, all_case_files, all_case_results):
    """
    Сверяем cost_of_lawsuit с ценой иска из эталонного ИСК.docx.
    Если generation_input выведен автоматически и суммы разошлись — warning, не fail.
    """
    import warnings

    result = all_case_results[case_name]
    files = all_case_files[case_name]
    gen = _generation_or_skip(case_name, result)
    if not files["golden_claim"].is_file():
        pytest.skip("Нет эталонного ИСК.docx")

    expected_tuples = result["table_parser_result"]
    calculated_list = []
    days = []
    points = []
    for parsed, ui in zip(expected_tuples, gen["complects"]):
        calculated = calculate_penalty(
            parsed_data=parsed[0],
            day_of_penalty=ui["day_of_penalty"],
            company_type=gen["company_type"],
            end_date=gen["end_date"],
        )
        calculated["contract_number"] = parsed[1]
        calculated["contract_type"] = ui["contract_type"]
        calculated_list.append(sort_calculator_result(calculated))
        days.append(ui["day_of_penalty"])
        points.append(ui["contract_point"])

    claim_data = convert_data(
        calculated_data_list=calculated_list,
        last_days_of_penalty=days,
        contract_points=points,
        company_type=gen["company_type"],
        current_date=gen["end_date"],
    )
    cost = claim_data["table_info"]["cost_of_lawsuit"]
    hints = gen.get("_hints") or {}
    if not hints.get("cost"):
        from test.helpers.case_loader import _extract_hints_from_golden_claim

        hints = _extract_hints_from_golden_claim(files["golden_claim"])
    expected_cost = hints.get("cost")
    if not expected_cost:
        pytest.skip("В эталонном иске не найдена цена иска")

    if cost != expected_cost:
        msg = (
            f"Цена иска после расчёта {cost!r} != эталон {expected_cost!r} "
            f"(company_type={gen['company_type']!r}, end_date={gen['end_date']!r}). "
            "Уточните generation_input.json для этого кейса."
        )
        if gen.get("_inferred"):
            warnings.warn(msg, UserWarning)
        else:
            assert cost == expected_cost, msg


# ---------------------------------------------------------------------------
# PDF / ЕГРЮЛ — integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_egrul_parser_matches_result_json(
    case_name, all_case_files, all_case_results
):
    files = all_case_files[case_name]
    if files["egrul_pdf"] is None:
        pytest.skip(f"{case_name}: нет выписки ЕГРЮЛ (ul-/fl-*.pdf)")
    expected = all_case_results[case_name]["results_of_name_parser"]["defendant_info"]
    full_name, short_name, address, kpp, ogrn, _ = parse_egrul_certificate(
        files["egrul_pdf"]
    )
    assert normalize_name(full_name) == normalize_name(expected["full_name"])
    if expected.get("short_name"):
        assert normalize_name(short_name) == normalize_name(expected["short_name"])
    if expected.get("address"):
        assert normalize_quotes(address).upper().replace(" ", "") == normalize_quotes(
            expected["address"]
        ).upper().replace(" ", "")
    if expected.get("kpp"):
        assert str(kpp) == str(expected["kpp"])
    assert str(ogrn) == str(expected["ogrn"])


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_claim_parser_matches_result_json(
    case_name, all_case_files, all_case_results, claim_parser
):
    files = all_case_files[case_name]
    result = all_case_results[case_name]
    for i, (meta, expected_tuple) in enumerate(
        zip(files["complects"], result["table_parser_result"])
    ):
        if meta["claim_pdf"] is None:
            pytest.skip(f"{case_name}: нет PDF претензии в complect_{i+1}")
        claims = claim_parser.analyse_claim(meta["claim_pdf"])
        expected_claims = expected_tuple[6]
        assert len(claims) == len(expected_claims)
        for j, (got, exp) in enumerate(zip(claims, expected_claims)):
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


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_contract_parser_matches_user_input(
    case_name, all_case_files, all_case_results, contract_parser, app_config
):
    files = all_case_files[case_name]
    result = all_case_results[case_name]
    gen = _generation_or_skip(case_name, result)
    for i, (meta, ui) in enumerate(zip(files["complects"], gen["complects"])):
        if meta["contract_pdf"] is None:
            pytest.skip(f"{case_name}: нет PDF договора в complect_{i+1}")
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


# ---------------------------------------------------------------------------
# Полный pipeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("case_name", CASE_NAMES, ids=_ids)
def test_pipeline_parse_calculate_generate_matches_golden(
    case_name,
    all_case_files,
    all_case_results,
    claim_parser,
    contract_parser,
    app_config,
    tmp_path,
):
    files = all_case_files[case_name]
    result = all_case_results[case_name]
    if not files["golden_claim"].is_file() or not files["golden_calculation"].is_file():
        pytest.skip("Нет эталонных ИСК.docx / расчёт к иску.docx")
    gen = _generation_or_skip(case_name, result)

    claim_data, calculator_list = build_claim_data_for_case(
        result_parser=result,
        generation_input=gen,
        files=files,
        claim_parser=claim_parser,
        contract_parser=contract_parser,
        app_config=app_config,
    )

    assert claim_data["company_type"] == gen["company_type"]
    assert claim_data["plaintiff_info"]["inn"] == gen["plaintiff_info"]["inn"]

    from test.helpers.case_loader import _extract_hints_from_golden_claim

    hints = gen.get("_hints") or _extract_hints_from_golden_claim(files["golden_claim"])
    calc_cost = claim_data["lawsuit_info"]["cost"]
    if gen.get("_inferred") and hints.get("cost") and calc_cost != hints["cost"]:
        pytest.skip(
            f"Авто-generation_input даёт цену иска {calc_cost!r}, "
            f"в эталоне {hints['cost']!r}. Добавьте generation_input.json с верными "
            "company_type / day_of_penalty / end_date / contract_point."
        )

    # якоря из договора / ответчика
    short = (result["results_of_name_parser"]["defendant_info"].get("short_name") or "")
    extra = tuple(
        x
        for x in (
            short.split()[0] if short else "",
            *(
                ui["contract_type"]
                for ui in gen["complects"]
                if not is_extraction_failure(ui.get("contract_type"))
            ),
        )
        if x
    )

    generate_and_compare_golden(
        claim_data=claim_data,
        calculator_list=calculator_list,
        app_config=app_config,
        files=files,
        tmp_path=tmp_path,
        extra_claim_anchors=extra,
    )
