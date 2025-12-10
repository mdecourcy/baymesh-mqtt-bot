#!/bin/bash
# Get bot command statistics
# Usage: ./scripts/bot_stats.sh [days]
# Example: ./scripts/bot_stats.sh 30

BASE_URL="${API_BASE_URL:-http://localhost:8000}"
DAYS="${1:-30}"

echo "Fetching bot statistics for last ${DAYS} days..."
curl -s "${BASE_URL}/bot/stats?days=${DAYS}" | jq .



