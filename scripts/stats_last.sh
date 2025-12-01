#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}

echo "GET /stats/last"
curl -sS "${API_BASE_URL}/stats/last"
echo
