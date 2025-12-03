#!/bin/bash
# Get log file statistics
# Usage: ./scripts/admin_logs.sh

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "Fetching log file statistics..."
curl -s "${BASE_URL}/admin/logs" | jq .


