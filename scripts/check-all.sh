#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/back"
./.venv/bin/python -m pytest -q

cd "$ROOT/app-presentateur"
npm run build

cd "$ROOT/mobile"
npx tsc --noEmit

