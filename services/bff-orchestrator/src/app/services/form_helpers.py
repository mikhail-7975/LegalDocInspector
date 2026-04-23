"""Build and merge form state with parse / calculation results."""

from __future__ import annotations

from datetime import date
from typing import Any

from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import calculate_state_duty


def _claims_from_row(claim_info: list[dict] | Any) -> list[str]:
    if not isinstance(claim_info, list):
        return []
    out = []
    for item in claim_info:
        if not isinstance(item, dict):
            continue
        num = item.get("claim_number", "")
        d = item.get("claim_date", "")
        out.append(f"№ {num} от {d}")
    return out


def default_form_from_parse(parse_result: dict[str, Any]) -> dict[str, Any]:
    di = parse_result.get("results_of_name_parser", {}).get("defendant_info", {})
    defendant_info = {
        "full_name": di.get("full_name", ""),
        "short_name": di.get("short_name", ""),
        "inn": di.get("inn", ""),
        "ogrn": di.get("ogrn", ""),
        "addres": di.get("address") or di.get("addres", ""),
    }
    court_info = {
        "name": "Арбитражный суд города Москвы",
        "addres": "115225, г. Москва, ул. Большая Тульская, д. 17",
    }
    plaintiff_info = {
        "inn": "7720518494",
        "full_name": "",
        "short_name": "",
        "addres": "",
        "correspondency_addres": "121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613",
        "ogrn": "",
    }
    complects: dict[str, Any] = {}
    all_claims: list[str] = []
    service_types: list[str] = []

    for row in parse_result.get("table_parser_result", []):
        merged, contract_number, contract_type, contract_point, overdue_day, _ct, claim_info = row
        try:
            day_int = int(str(overdue_day).strip()) if str(overdue_day).strip().isdigit() else 18
        except Exception:
            day_int = 18
        complects[contract_number] = {
            "contract_type": contract_type,
            "contract_point": contract_point,
            "day_of_penalty": day_int,
        }
        if contract_type and contract_type not in service_types:
            service_types.append(contract_type)
        all_claims.extend(_claims_from_row(claim_info))

    app_date = parse_result.get("application_date") or date.today().strftime("%d.%m.%Y")

    return {
        "court_info": court_info,
        "plaintiff_info": plaintiff_info,
        "defendant_info": defendant_info,
        "lawsuit_info": {
            "cost": "",
            "tax": "",
            "service_type": "".join(service_types) if service_types else "ТЭ",
            "claims": all_claims,
        },
        "complects": complects,
        "company_type": "ТСЖ",
        "end_date": app_date,
        "responsitive_name": "",
    }


def merge_claim_for_documents(
    claim_data: dict[str, Any],
    form_state: dict[str, Any],
) -> dict[str, Any]:
    claim = dict(claim_data)
    claim["plaintiff_info"] = form_state["plaintiff_info"]
    d = dict(form_state["defendant_info"])
    if "addres" not in d and d.get("address"):
        d["addres"] = d["address"]
    claim["defendant_info"] = d
    claim["lawsuit_info"] = form_state["lawsuit_info"]
    claim["responsitive_name"] = form_state.get("responsitive_name") or ""
    return claim


def build_calculate_body(parse_result: dict[str, Any], form_state: dict[str, Any]) -> dict[str, Any]:
    complects = form_state.get("complects", {})
    parsing_results: list[dict[str, Any]] = []
    for row in parse_result["table_parser_result"]:
        merged, contract_number, contract_type, contract_point, overdue_day, _ctxt, _cinfo = row
        c = complects.get(contract_number, {})
        try:
            default_day = int(str(overdue_day).strip()) if str(overdue_day).strip().isdigit() else 18
        except Exception:
            default_day = 18
        day = c.get("day_of_penalty", default_day)
        parsing_results.append(
            {
                "parsed_info": merged,
                "contract_number": contract_number,
                "contract_type": c.get("contract_type") or contract_type,
                "contract_point": c.get("contract_point") or contract_point,
                "day_of_penalty": int(day),
            }
        )
    return {
        "company_type": form_state["company_type"],
        "end_date": form_state["end_date"],
        "parsing_results": parsing_results,
    }


def apply_calculate_to_form(form_state: dict[str, Any], claim_data: dict[str, Any]) -> dict[str, Any]:
    fs = dict(form_state)
    ti = claim_data.get("table_info", {})
    cost = ti.get("cost_of_lawsuit", "")
    fs["lawsuit_info"] = dict(fs.get("lawsuit_info", {}))
    fs["lawsuit_info"]["cost"] = str(cost)
    try:
        fs["lawsuit_info"]["tax"] = calculate_state_duty(str(cost))
    except Exception:
        fs["lawsuit_info"]["tax"] = ""
    return fs


def deserialize_parse_result(data: dict[str, Any]) -> dict[str, Any]:
    """Restore tuple rows expected by calculate pipeline."""
    out = dict(data)
    rows: list[tuple[Any, ...]] = []
    for item in data.get("table_parser_result", []):
        rows.append(
            (
                item["parsed_info"],
                item["contract_number"],
                item["contract_type"],
                item["contract_point"],
                item["overdue_day"],
                item["contract_text"],
                item["claim_info"],
            )
        )
    out["table_parser_result"] = rows
    return out


def serialize_parse_for_api(parse_result: dict[str, Any]) -> dict[str, Any]:
    out = dict(parse_result)
    rows: list[dict[str, Any]] = []
    for row in parse_result.get("table_parser_result", []):
        merged, cn, ct, cp, od, ctxt, cinfo = row
        rows.append(
            {
                "parsed_info": merged,
                "contract_number": cn,
                "contract_type": ct,
                "contract_point": cp,
                "overdue_day": od,
                "contract_text": ctxt,
                "claim_info": cinfo,
            }
        )
    out["table_parser_result"] = rows
    return out
