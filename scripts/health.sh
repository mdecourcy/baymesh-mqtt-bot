#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}

echo "GET /health"
curl -sS "${API_BASE_URL}/health"
echo
