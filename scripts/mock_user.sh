#!/usr/bin/env bash
set -euo pipefail
API_BASE_URL=${API_BASE_URL:-"http://localhost:8000"}
USER_ID=${1:?"Usage: $0 USER_ID USERNAME [MESH_ID]"}
USERNAME=${2:?"Usage: $0 USER_ID USERNAME [MESH_ID]"}
MESH_ID=${3:-"mesh${USER_ID}"}

read -r -d '' PAYLOAD <<JSON || true
{
  "user_id": ${USER_ID},
  "username": "${USERNAME}",
  "mesh_id": "${MESH_ID}"
}
JSON

echo "POST /mock/user"
curl -sS -X POST "${API_BASE_URL}/mock/user" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}"
echo
