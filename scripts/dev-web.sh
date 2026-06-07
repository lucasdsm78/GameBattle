#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../app-presentateur"
npm install
npm run dev

