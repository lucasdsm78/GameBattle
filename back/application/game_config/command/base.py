from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.model.game_config import GameConfig
from domain.game_config.repository.game_config_repository import GameConfigRepository

ConfigTransform = Callable[[GameConfig], GameConfig | Awaitable[GameConfig]]


class GameConfigCommandBase:
    """Plomberie partagée par tous les use cases de commande GameConfig.

    Centralise le cycle de vie *charger → transformer → valider → persister → mapper*
    autour de l'unique agrégat GameConfig.
    """

    def __init__(self, repository: GameConfigRepository) -> None:
        self.repository = repository

    async def _persist(self, config: GameConfig) -> GameConfigReadModel:
        """Valide la config, la sauvegarde et la mappe vers le modèle de lecture."""
        config.validate()
        persisted = await self.repository.save(config)
        return GameConfigReadModel.from_domain(persisted)

    async def _mutate(self, transform: ConfigTransform) -> GameConfigReadModel:
        """Charge la config courante, applique `transform` (sync ou async), valide et persiste."""
        result = transform(await self.repository.get_current())
        updated = await result if isawaitable(result) else result
        return await self._persist(updated)
