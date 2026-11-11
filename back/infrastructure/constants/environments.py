"""Environnements locaux : tout autre nom est traité comme un déploiement (HTTPS, secrets obligatoires)."""

from __future__ import annotations

# Seuls environnements « locaux » : tout autre nom (staging, recette, production…) est un déploiement, avec les
# mêmes exigences. Une faute de frappe dans GAMEBATTLE_ENVIRONMENT durcit la configuration au lieu de l'affaiblir.
LOCAL_ENVIRONMENTS = frozenset({"development", "dev", "local", "test"})
