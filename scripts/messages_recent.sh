#!/bin/bash
# Get recent messages
# Usage: ./scripts/messages_recent.sh [limit]
# Example: ./scripts/messages_recent.sh 20

BASE_URL="${API_BASE_URL:-http://localhost:8000}"
LIMIT="${1:-100}"

echo "Fetching last ${LIMIT} messages..."
curl -s "${BASE_URL}/messages/recent?limit=${LIMIT}" | jq .


