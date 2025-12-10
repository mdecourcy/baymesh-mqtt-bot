#!/bin/bash
# Get comparison statistics (day-over-day, week-over-week, month-over-month)
# Usage: ./scripts/comparison_stats.sh

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "Fetching comparison statistics..."
curl -s "${BASE_URL}/stats/comparisons" | jq .



