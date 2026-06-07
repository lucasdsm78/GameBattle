#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../back"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload

