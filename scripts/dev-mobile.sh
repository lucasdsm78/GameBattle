#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../mobile"
npm install
npm run start

