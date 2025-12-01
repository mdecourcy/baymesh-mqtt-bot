#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
ENV_FILE="${ROOT_DIR}/.env.heltec"

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env.heltec not found at $ENV_FILE" >&2
  exit 1
fi

if [[ ! -f "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Virtualenv not found. Create one with 'python3.11 -m venv .venv'" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a
export MESHTASTIC_ENV_FILE="$ENV_FILE"

cd "$ROOT_DIR"
exec .venv/bin/python main.py
