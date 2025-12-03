#!/bin/bash
# Test the daily broadcast feature
# Usage: ./scripts/test_broadcast.sh

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "Triggering test broadcast..."
curl -X POST "${BASE_URL}/admin/test-broadcast" \
  -H "Content-Type: application/json" \
  | jq .

echo ""
echo "Broadcast sent! Check your Meshtastic device for the message."


