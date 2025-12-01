#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
USER_ID=${1:?"Usage: $0 USER_ID"}

echo "DELETE /subscribe/${USER_ID}"
curl -sS -X DELETE "${API_BASE_URL}/subscribe/${USER_ID}"
echo
