#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
COUNT=${1:-5}

echo "GET /stats/last/${COUNT}"
curl -sS "${API_BASE_URL}/stats/last/${COUNT}"
echo
