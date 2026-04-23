"""Penalty calculation via legacy modules (no edits to penalty_calculator.py)."""

from __future__ import annotations

from typing import Any

from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import (
    calculate_penalty,
)
from LegalDocInspector.legal_doc_inspector.utils.calculator_adapter import convert_data


def sort_data_structure(data: dict) -> dict:
    """Same ordering as legacy Flask routes (for DOCX generator stability)."""
    sorted_data: dict = {}
    if "start_of_table" in data:
        sorted_data["start_of_table"] = data["start_of_table"]

    months: list[tuple] = []
    for key in data.keys():
        if isinstance(key, str) and len(key.split()) == 2:
            try:
                month_name, year_str = key.split()
                year = int(year_str)
                months.append((key, year, month_name))
            except (ValueError, IndexError):
                continue

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

    def month_sort_key(item: tuple) -> tuple:
        key, year, month_name = item
        return (year, month_order.get(month_name, 99))

    sorted_months = sorted(months, key=month_sort_key)
    for month_key, _, _ in sorted_months:
        sorted_data[month_key] = data[month_key]

    elements_order = [
        "end_of_table1",
        "end_of_table2",
        "debt_info",
        "contract_number",
        "contract_type",
    ]
    for element in elements_order:
        if element in data:
            sorted_data[element] = data[element]

    return sorted_data


def run_calculate(data: dict[str, Any]) -> dict[str, Any]:
    """Same contract as Flask POST /calculate_penalty."""
    calculated_results: list[dict[str, Any]] = []
    last_days_of_penalty: list[Any] = []
    contract_points: list[str] = []
    for parsing_result in data["parsing_results"]:
        calculated_data = calculate_penalty(
            parsed_data=parsing_result["parsed_info"],
            day_of_penalty=parsing_result["day_of_penalty"],
            company_type=data["company_type"],
            end_date=data["end_date"],
        )
        calculated_data["contract_number"] = parsing_result["contract_number"]
        calculated_data["contract_type"] = parsing_result["contract_type"]
        last_days_of_penalty.append(parsing_result["day_of_penalty"])
        contract_points.append(parsing_result["contract_point"])
        calculated_results.append(sort_data_structure(calculated_data))

    converted_data = convert_data(
        calculated_data_list=calculated_results,
        last_days_of_penalty=last_days_of_penalty,
        contract_points=contract_points,
        company_type=data["company_type"],
        current_date=data["end_date"],
    )
    return {"claim_data": converted_data, "calculator_list": calculated_results}
