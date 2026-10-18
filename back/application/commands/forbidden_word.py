from __future__ import annotations

from application.commands.base import CommandUseCase
from application.commands.payloads import ForbiddenWordCardCommand
from application.services.snapshot import GameConfigSnapshot


class ForbiddenWordCommandUseCase(CommandUseCase):
    """TROUVÉ / PASSER sont idempotents grâce à l'identifiant de carte : un doublon ne diffuse rien."""

    async def start_turn(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_forbidden_word_turn(ctx.now_ms))

    async def mark_found(self, command: ForbiddenWordCardCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.resolve_forbidden_word_card(command.card_id, found=True, now_ms=ctx.now_ms))

    async def skip(self, command: ForbiddenWordCardCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.resolve_forbidden_word_card(command.card_id, found=False, now_ms=ctx.now_ms))
