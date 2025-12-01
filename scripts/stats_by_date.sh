#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
DATE=${1:?"Usage: $0 YYYY-MM-DD"}

echo "GET /stats/${DATE}"
curl -sS "${API_BASE_URL}/stats/${DATE}"
echo
