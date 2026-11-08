#!/usr/bin/env bash
# Rejoue les migrations Alembic sur un vrai PostgreSQL jetable (Docker), comme en production :
# 0002 + données → head, schéma comparé à celui des modèles, clés étrangères, verrou optimiste, descente vers 0002.
# Ne touche à aucune base existante : le conteneur est créé pour l'occasion puis supprimé.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="gamebattle-migrations-$$"
PASSWORD="$(openssl rand -hex 16)"
IMAGE="${GAMEBATTLE_POSTGRES_IMAGE:-postgres:15-alpine}"  # même version que docker-compose et la production

docker run -d --rm --name "$NAME" -e POSTGRES_USER=gamebattle -e POSTGRES_PASSWORD="$PASSWORD" \
  -e POSTGRES_DB=migrations -p 127.0.0.1::5432 "$IMAGE" >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 60); do
  docker exec "$NAME" pg_isready -U gamebattle -d migrations >/dev/null 2>&1 && break
  sleep 0.5
done
PORT="$(docker port "$NAME" 5432/tcp | head -n1 | awk -F: '{print $NF}')"

cd "$ROOT/back"
GAMEBATTLE_TEST_POSTGRES_URL="postgresql+asyncpg://gamebattle:${PASSWORD}@127.0.0.1:${PORT}/migrations" \
  ./.venv/bin/python -m pytest tests/infrastructure/test_migrations_postgres.py -v "$@"
