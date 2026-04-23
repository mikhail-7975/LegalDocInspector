#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "Run each component in a separate terminal:"
echo
echo "Terminal 1 (API):"
echo "  cd \"$ROOT\" && ./start_api.sh"
echo
echo "Terminal 2 (Parser worker):"
echo "  cd \"$ROOT\" && ./start_parser_worker.sh"
echo
echo "Terminal 3 (Doc generator worker):"
echo "  cd \"$ROOT\" && ./start_doc_generator_worker.sh"
echo
echo "Optional client command:"
echo "  cd \"$ROOT\" && python -m demo_app.client.http_demo_client"
