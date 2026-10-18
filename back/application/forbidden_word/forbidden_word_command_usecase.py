from __future__ import annotations

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import ForbiddenWordCardCommandModel, GameConfigReadModel


class ForbiddenWordCommandUseCase(GameConfigCommandBase):
    async def start_turn(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_forbidden_word_turn(self._now_ms()))

    async def mark_found(self, payload: ForbiddenWordCardCommandModel) -> GameConfigReadModel | None:
        return await self._mutate_if_changed(
            lambda config: config.resolve_forbidden_word_card(payload.card_id, found=True, now_ms=self._now_ms())
        )

    async def skip(self, payload: ForbiddenWordCardCommandModel) -> GameConfigReadModel | None:
        return await self._mutate_if_changed(
            lambda config: config.resolve_forbidden_word_card(payload.card_id, found=False, now_ms=self._now_ms())
        )
