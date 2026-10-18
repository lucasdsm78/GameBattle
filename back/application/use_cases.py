from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from application.auction.auction_command_usecase import AuctionCommandUseCase
from application.blindtest.blindtest_command_usecase import BlindtestCommandUseCase
from application.blindtest.playlist_service import BlindtestPlaylistService
from application.bombe.bombe_command_usecase import BombeCommandUseCase
from application.culture.culture_command_usecase import CultureCommandUseCase
from application.forbidden_word.forbidden_word_command_usecase import (
    ForbiddenWordCommandUseCase,
)
from application.game_night.game_night_command_usecase import GameNightCommandUseCase
from application.memory.memory_command_usecase import MemoryCommandUseCase
from application.seven_differences.seven_differences_command_usecase import (
    SevenDifferencesCommandUseCase,
)
from application.shared.command_usecase import (
    CommandUseCase,
    SnapshotPublisher,
    wall_clock_ms,
)
from application.shared.unit_of_work import UnitOfWork
from application.stopchrono.stopchrono_command_usecase import StopChronoCommandUseCase


@dataclass(frozen=True, slots=True)
class GameUseCases:
    """Ensemble des use cases d'écriture, partageant la même unité de travail, le même diffuseur et la même horloge."""

    game_night: GameNightCommandUseCase
    blindtest: BlindtestCommandUseCase
    stopchrono: StopChronoCommandUseCase
    culture: CultureCommandUseCase
    bombe: BombeCommandUseCase
    memory: MemoryCommandUseCase
    seven_differences: SevenDifferencesCommandUseCase
    auction: AuctionCommandUseCase
    forbidden_word: ForbiddenWordCommandUseCase

    @classmethod
    def build(
        cls,
        uow: UnitOfWork,
        publisher: SnapshotPublisher,
        playlists: BlindtestPlaylistService,
        clock: Callable[[], int] = wall_clock_ms,
    ) -> GameUseCases:
        dependencies = (uow, publisher, playlists, clock)
        return cls(
            game_night=GameNightCommandUseCase(*dependencies),
            blindtest=BlindtestCommandUseCase(*dependencies),
            stopchrono=StopChronoCommandUseCase(*dependencies),
            culture=CultureCommandUseCase(*dependencies),
            bombe=BombeCommandUseCase(*dependencies),
            memory=MemoryCommandUseCase(*dependencies),
            seven_differences=SevenDifferencesCommandUseCase(*dependencies),
            auction=AuctionCommandUseCase(*dependencies),
            forbidden_word=ForbiddenWordCommandUseCase(*dependencies),
        )

__all__ = ["CommandUseCase", "GameUseCases", "SnapshotPublisher"]
