#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
USER_ID=${1:?"Usage: $0 USER_ID SUBSCRIPTION_TYPE"}
SUB_TYPE=${2:?"Usage: $0 USER_ID SUBSCRIPTION_TYPE"}

echo "POST /subscribe/${USER_ID}/${SUB_TYPE}"
curl -sS -X POST "${API_BASE_URL}/subscribe/${USER_ID}/${SUB_TYPE}"
echo
