from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerIdentity:
    """Le joueur connecté, tel que le module comptes le garantit aux autres modules (salons…).

    Contrat entre modules : les salons ne lisent jamais les tables ni le code des comptes, seulement ceci.
    """

    account_id: str
    pseudo: str
