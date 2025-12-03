#!/bin/bash
# Get recent bot commands
# Usage: ./scripts/bot_commands_recent.sh [limit]
# Example: ./scripts/bot_commands_recent.sh 20

BASE_URL="${API_BASE_URL:-http://localhost:8000}"
LIMIT="${1:-50}"

echo "Fetching last ${LIMIT} bot commands..."
curl -s "${BASE_URL}/bot/commands/recent?limit=${LIMIT}" | jq .


