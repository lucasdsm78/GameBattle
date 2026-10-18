from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from application.commands.auction import AuctionCommandUseCase
from application.commands.base import CommandUseCase, SnapshotPublisher, wall_clock_ms
from application.commands.blindtest import BlindtestCommandUseCase
from application.commands.bombe import BombeCommandUseCase
from application.commands.culture import CultureCommandUseCase
from application.commands.forbidden_word import ForbiddenWordCommandUseCase
from application.commands.memory import MemoryCommandUseCase
from application.commands.session import SessionCommandUseCase
from application.commands.seven_differences import SevenDifferencesCommandUseCase
from application.commands.stopchrono import StopChronoCommandUseCase
from application.services.playlist import BlindtestPlaylistService
from domain.repositories.game_config import GameConfigRepository


@dataclass(frozen=True, slots=True)
class GameUseCases:
    """Ensemble des use cases d'écriture, partageant le même dépôt, le même diffuseur et la même horloge."""

    session: SessionCommandUseCase
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
        repository: GameConfigRepository,
        publisher: SnapshotPublisher,
        playlists: BlindtestPlaylistService,
        clock: Callable[[], int] = wall_clock_ms,
    ) -> GameUseCases:
        dependencies = (repository, publisher, playlists, clock)
        return cls(
            session=SessionCommandUseCase(*dependencies),
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
