from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from infrastructure.constants.database_locks import API_INSTANCE_LOCK_ID
from infrastructure.database.database import Database


class AnotherInstanceRunningError(RuntimeError):
    pass


class SingleInstanceLock:
    """Une seule instance de l'API par base de données.

    L'API garde en mémoire l'état des parties, le hub WebSocket, les verrous d'écriture et les minuteurs (chronos
    des jeux, ménage des comptes) : un deuxième processus (`--workers 2`, une réplique…) jouerait les mêmes
    échéances en double et diffuserait des états divergents. Un verrou consultatif PostgreSQL, tenu par une
    connexion dédiée pendant toute la vie du processus, fait donc échouer le démarrage d'une seconde instance.
    PostgreSQL le libère de lui-même si le processus meurt. SQLite (tests) n'en a pas besoin.
    """

    def __init__(self, database: Database) -> None:
        self._database = database
        self._connection: Optional[AsyncConnection] = None

    async def acquire(self) -> None:
        if self._database.dialect_name != "postgresql" or self._connection is not None:
            return
        connection = await self._database.connect()
        try:
            acquired = await connection.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": API_INSTANCE_LOCK_ID})
            await connection.commit()  # le verrou appartient à la session, pas à la transaction : on ne reste pas « idle in transaction »
        except BaseException:
            await connection.close()
            raise
        if not acquired:
            await connection.close()
            raise AnotherInstanceRunningError(
                "Une autre instance de l'API GameBattle tourne déjà sur cette base : l'état des parties est en mémoire, "
                "il ne peut y avoir qu'un seul processus (pas de `--workers`, pas de réplique)."
            )
        self._connection = connection

    async def release(self) -> None:
        if self._connection is None:
            return
        try:
            await self._connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": API_INSTANCE_LOCK_ID})
            await self._connection.commit()
        finally:
            await self._connection.close()
            self._connection = None
