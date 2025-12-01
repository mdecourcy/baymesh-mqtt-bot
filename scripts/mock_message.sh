#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
USER_ID=${1:?"Usage: $0 USER_ID [GATEWAY_COUNT]"}
GATEWAYS=${2:-5}
TIMESTAMP=${3:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}

read -r -d '' PAYLOAD <<JSON || true
{
  "sender_id": ${USER_ID},
  "sender_name": "TestUser${USER_ID}",
  "gateway_count": ${GATEWAYS},
  "rssi": -100,
  "snr": 5.0,
  "payload": "mock payload",
  "timestamp": "${TIMESTAMP}"
}
JSON

echo "POST /mock/message"
curl -sS -X POST "${API_BASE_URL}/mock/message" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}"
echo
