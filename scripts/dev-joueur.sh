#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../app-joueur"
npm install
npm run dev
