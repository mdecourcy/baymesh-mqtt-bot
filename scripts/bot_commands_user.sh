#!/bin/bash
# Get command history for a specific user
# Usage: ./scripts/bot_commands_user.sh <user_id> [limit]
# Example: ./scripts/bot_commands_user.sh 3610035310 20

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

if [ -z "$1" ]; then
  echo "Error: user_id required"
  echo "Usage: $0 <user_id> [limit]"
  exit 1
fi

USER_ID="$1"
LIMIT="${2:-50}"

echo "Fetching command history for user ${USER_ID}..."
curl -s "${BASE_URL}/bot/commands/user/${USER_ID}?limit=${LIMIT}" | jq .

