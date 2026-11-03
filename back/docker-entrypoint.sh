#!/bin/sh
# Production : le schéma n'évolue que par les migrations, appliquées avant d'ouvrir le port.
# `--no-proxy-headers` : l'adresse du joueur est déterminée par l'application (GAMEBATTLE_TRUSTED_PROXIES),
# à partir de la vraie connexion TCP ; uvicorn ne réécrit rien.
set -eu
alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8000 --ws-max-size 65536 --no-server-header --no-proxy-headers
