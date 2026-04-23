#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001/api/v1}"
STATE_FILE="${STATE_FILE:-.demo_package_id}"

command -v curl >/dev/null 2>&1 || { echo "curl not found"; exit 1; }
command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || { echo "python not found"; exit 1; }
PY_CMD="$(command -v python || command -v python3)"

echo "Creating package..."
PACKAGE_RESP="$(curl -sS -X POST "$API_BASE/packages")"

PACKAGE_ID="$("$PY_CMD" - <<'PY' "$PACKAGE_RESP"
import json
import sys

payload = json.loads(sys.argv[1])
package_id = payload.get("package_id")
if not package_id:
    raise SystemExit("package_id was not returned by API")
print(package_id)
PY
)"

echo "$PACKAGE_ID" > "$STATE_FILE"
echo "package_id=$PACKAGE_ID (saved to $STATE_FILE)"

INITIAL_JSON="$("$PY_CMD" - <<'PY'
import json

payload = {
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
print(json.dumps(payload, ensure_ascii=False))
PY
)"

echo "Sending initial JSON to /parse..."
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -d "$INITIAL_JSON" \
  "$API_BASE/packages/$PACKAGE_ID/parse"
echo
echo "Parse request sent."
