#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! docker info >/dev/null 2>&1; then
  echo "Docker doit être démarré pour lancer PostgreSQL." >&2
  exit 1
fi

cd "$ROOT"
docker compose up -d --wait db

cd "$ROOT/back"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload


