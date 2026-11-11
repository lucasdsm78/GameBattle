from __future__ import annotations

from dataclasses import dataclass

from application.shared.player_identity import PlayerIdentity


@dataclass(frozen=True, slots=True)
class AccountView:
    pseudo: str
    account_id: str = ""  # interne : jamais renvoyé par l'API, transmis aux autres modules via `PlayerIdentity`

    @property
    def identity(self) -> PlayerIdentity:
        return PlayerIdentity(account_id=self.account_id, pseudo=self.pseudo)
