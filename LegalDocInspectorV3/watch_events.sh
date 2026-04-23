#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001/api/v1}"
STATE_FILE="${STATE_FILE:-.demo_package_id}"
SINCE="${SINCE:-0}"
INTERVAL_SEC="${INTERVAL_SEC:-1}"

PY_CMD="$(command -v python || command -v python3 || true)"
if [[ -z "$PY_CMD" ]]; then
  echo "python not found"
  exit 1
fi

if [[ $# -ge 1 && -n "${1:-}" ]]; then
  PACKAGE_ID="$1"
elif [[ -f "$STATE_FILE" ]]; then
  PACKAGE_ID="$(<"$STATE_FILE")"
else
  echo "package_id is required. Pass it as first argument or create $STATE_FILE."
  exit 1
fi

echo "Watching events for package_id=$PACKAGE_ID"
echo "API_BASE=$API_BASE, start since=$SINCE, interval=${INTERVAL_SEC}s"
echo "Press Ctrl+C to stop."

while true; do
  RESP="$(curl -sS "$API_BASE/packages/$PACKAGE_ID/events?since=$SINCE")"
  OUT="$("$PY_CMD" -c '
import json
import sys

payload = json.loads(sys.argv[1])
events = payload.get("events", [])
for event in events:
    print(json.dumps(event, ensure_ascii=False))
print("NEXT=" + str(payload.get("next_offset", 0)))
' "$RESP")"

  printf "%s\n" "$OUT" | "$PY_CMD" -c '
import sys

lines = sys.stdin.read().splitlines()
if not lines:
    print("NEXT=0")
    raise SystemExit(0)

for line in lines[:-1]:
    if line:
        print(line)
print(lines[-1])
'

  SINCE="$(printf "%s\n" "$OUT" | "$PY_CMD" -c '
import sys

lines = sys.stdin.read().splitlines()
if not lines:
    print("0")
    raise SystemExit(0)

last = lines[-1]
if last.startswith("NEXT="):
    print(last[5:])
else:
    print("0")
')"

  sleep "$INTERVAL_SEC"
done
