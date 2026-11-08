"""Modèles ORM, rangés par module du monolithe (un sous-paquet ou un fichier par module).

Aucun ré-export ici : chaque module importe ses propres modèles, jamais ceux d'un autre module. Pour enregistrer
toutes les tables (Alembic, `create_all`), importer `infrastructure.database.all_models`.
"""
