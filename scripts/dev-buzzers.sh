#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_PATH="${1:-$ROOT/scripts/hardware-buzzers.example.json}"
API_BASE_URL="${GAMEBATTLE_HARDWARE_API_BASE_URL:-http://127.0.0.1:8000}"
HARDWARE_TOKEN="${GAMEBATTLE_HARDWARE_TOKEN:-change-me-hardware}"

cd "$ROOT/back"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m infrastructure.hardware.usb_buzzer_bridge \
  --config "$CONFIG_PATH" \
  --api-base-url "$API_BASE_URL" \
  --hardware-token "$HARDWARE_TOKEN"

