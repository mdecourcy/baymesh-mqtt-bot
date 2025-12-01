#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
TYPE_FILTER=${1:-}

if [[ -n "$TYPE_FILTER" ]]; then
  URL="${API_BASE_URL}/subscriptions?subscription_type=${TYPE_FILTER}"
else
  URL="${API_BASE_URL}/subscriptions"
fi

echo "GET ${URL}"
curl -sS "${URL}"
echo
