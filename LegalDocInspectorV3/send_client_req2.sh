#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001/api/v1}"
STATE_FILE="${STATE_FILE:-.demo_package_id}"

command -v curl >/dev/null 2>&1 || { echo "curl not found"; exit 1; }
command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || { echo "python not found"; exit 1; }
PY_CMD="$(command -v python || command -v python3)"

if [[ $# -ge 1 && -n "${1:-}" ]]; then
  PACKAGE_ID="$1"
elif [[ -f "$STATE_FILE" ]]; then
  PACKAGE_ID="$(<"$STATE_FILE")"
else
  echo "package_id is required. Pass it as arg or run send_client_req1.sh first."
  exit 1
fi

echo "Using package_id=$PACKAGE_ID"
echo "Fetching parsed JSON from /parsed..."
PARSED_JSON="$(curl -sS "$API_BASE/packages/$PACKAGE_ID/parsed")"

EDITED_JSON="$("$PY_CMD" - <<'PY' "$PARSED_JSON"
import json
import sys

payload = json.loads(sys.argv[1])
payload["notes"] = f"{payload.get('notes', '')} (отредактировано пользователем)".strip()
payload["claim_amount"] = float(payload.get("claim_amount", 0)) + 1000.0
print(json.dumps(payload, ensure_ascii=False))
PY
)"

echo "Sending edited JSON to /generate..."
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -d "$EDITED_JSON" \
  "$API_BASE/packages/$PACKAGE_ID/generate"
echo
echo "Generate request sent."
