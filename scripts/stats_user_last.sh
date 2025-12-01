#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
USER_ID=${1:?"Usage: $0 USER_ID"}

echo "GET /stats/user/${USER_ID}/last"
curl -sS "${API_BASE_URL}/stats/user/${USER_ID}/last"
echo
