from __future__ import annotations

import json
import time
from typing import Any

import requests


API_BASE = "http://127.0.0.1:8001/api/v1"


def _sample_payload() -> dict[str, Any]:
    return {
        "application_date": "2026-04-23",
        "plaintiff_name": "ООО Ромашка",
        "defendant_name": "ТСЖ Север",
        "claim_amount": 123456.78,
        "files": [
            {"file_name": "contract.pdf", "file_type": "application/pdf", "file_size": 120034},
            {"file_name": "claim.pdf", "file_type": "application/pdf", "file_size": 54012},
            {
                "file_name": "certificate.xlsx",
                "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "file_size": 40011,
            },
        ],
        "notes": "Демо-пакет",
    }


def _poll_events(package_id: str, until_event: str) -> None:
    offset = 0
    while True:
        resp = requests.get(f"{API_BASE}/packages/{package_id}/events", params={"since": offset}, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        events = payload["events"]
        offset = payload["next_offset"]
        for event in events:
            print(json.dumps(event, ensure_ascii=False))
            if event["event_type"] == until_event:
                return
        time.sleep(2)


def main() -> None:
    package = requests.post(f"{API_BASE}/packages", timeout=10).json()
    package_id = package["package_id"]
    print(f"package_id={package_id}")

    initial_payload = _sample_payload()
    resp = requests.post(f"{API_BASE}/packages/{package_id}/parse", json=initial_payload, timeout=10)
    resp.raise_for_status()
    print("parse command accepted")

    _poll_events(package_id, "event.package.parsed")
    parsed = requests.get(f"{API_BASE}/packages/{package_id}/parsed", timeout=10).json()
    print("parsed data:", json.dumps(parsed, ensure_ascii=False))

    edited_payload = dict(parsed)
    edited_payload["notes"] = f"{parsed['notes']} (отредактировано пользователем)"
    edited_payload["claim_amount"] = float(parsed["claim_amount"]) + 1000.0
    resp = requests.post(f"{API_BASE}/packages/{package_id}/generate", json=edited_payload, timeout=10)
    resp.raise_for_status()
    print("generate command accepted")

    _poll_events(package_id, "event.package.completed")
    print("demo completed")


if __name__ == "__main__":
    main()
