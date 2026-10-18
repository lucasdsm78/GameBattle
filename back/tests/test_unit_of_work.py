from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from application.game_night.game_night_query_usecase import GameNightQueryUseCase
from domain.forbidden_word.events import TurnStarted, WordFound
from domain.game_night.models.game_config import GameConfig
from infrastructure.repositories.unit_of_work import GameConfigUnitOfWork
from support import GameHarness, InMemoryRepository, started_config


def _rename(config: GameConfig, suffix: str) -> GameConfig:
    return replace(config, settings=replace(config.settings, game_title=config.settings.game_title + suffix))


def test_commit_persists_the_aggregate_without_events_and_hands_them_over() -> None:
    repository = InMemoryRepository(started_config("auction").pull_events()[0])
    uow = GameConfigUnitOfWork(repository)

    async def scenario():
        async with uow:
            current = await uow.game_configs.get_current()
            uow.add(current.start_auction()._record(TurnStarted("Rouges")))
            return await uow.commit()

    saved, events = asyncio.run(scenario())

    assert events == (TurnStarted("Rouges"),)
    assert repository.saves == 1
    assert repository.current is saved
    assert saved.pending_events == ()
    assert saved.session.auction.phase == "bidding"


def test_leaving_without_commit_discards_the_staged_state() -> None:
    repository = InMemoryRepository(started_config("auction"))
    uow = GameConfigUnitOfWork(repository)

    async def scenario():
        async with uow:
            uow.add(_rename(await uow.game_configs.get_current(), " modifié"))

    asyncio.run(scenario())

    assert repository.saves == 0


def test_an_exception_rolls_back_and_releases_the_transaction() -> None:
    repository = InMemoryRepository(started_config("auction"))
    uow = GameConfigUnitOfWork(repository)

    async def failing():
        async with uow:
            uow.add(_rename(await uow.game_configs.get_current(), " modifié"))
            raise RuntimeError("panne")

    async def scenario():
        with pytest.raises(RuntimeError, match="panne"):
            await failing()
        async with uow:
            uow.add(_rename(await uow.game_configs.get_current(), " ok"))
            await uow.commit()

    asyncio.run(scenario())

    assert repository.saves == 1
    assert repository.current.settings.game_title.endswith(" ok")
    assert "modifié" not in repository.current.settings.game_title


def test_commit_without_staged_state_is_refused() -> None:
    uow = GameConfigUnitOfWork(InMemoryRepository(started_config("auction")))

    async def scenario():
        async with uow:
            await uow.commit()

    with pytest.raises(RuntimeError, match="Aucun état"):
        asyncio.run(scenario())


def test_transactions_are_serialized_so_no_update_is_lost() -> None:
    repository = InMemoryRepository(started_config("auction"), delay_seconds=0.005)
    uow = GameConfigUnitOfWork(repository)

    async def append(suffix: str) -> None:
        async with uow:
            current = await uow.game_configs.get_current()
            await asyncio.sleep(0.01)
            uow.add(_rename(current, suffix))
            await uow.commit()

    async def scenario():
        await asyncio.gather(append("A"), append("B"))

    asyncio.run(scenario())

    title = repository.current.settings.game_title
    assert title.endswith(("AB", "BA"))
    assert repository.saves == 2


class _FailingRepository(InMemoryRepository):
    async def save(self, game_config: GameConfig) -> GameConfig:
        raise ConnectionError("base indisponible")


def test_nothing_is_published_when_persistence_fails() -> None:
    harness = GameHarness(started_config("auction"))
    initial = harness.config
    harness.repository = harness.uow.game_configs = _FailingRepository(initial)  # type: ignore[misc]

    with pytest.raises(ConnectionError):
        asyncio.run(harness.use_cases.auction.start())

    assert harness.publisher.snapshots == []
    assert harness.repository.current is initial


def test_each_command_publishes_only_its_own_events() -> None:
    harness = GameHarness(started_config("forbidden_word").pull_events()[0], now_ms=2_000)
    team = harness.config.session.forbidden_word.turn_order[0]

    started = harness.run("forbidden-word.start-turn")
    card = harness.config.session.forbidden_word.current_card
    assert card is not None
    found = harness.run("forbidden-word.found", {"card_id": card.id})

    assert started.events == ({"type": TurnStarted.name, "team": team},)
    assert found.events == ({"type": WordFound.name, "team": team, "word": card.word},)
    assert harness.config.pending_events == ()
    assert [snapshot.events for snapshot in harness.publisher.snapshots] == [started.events, found.events]


def test_queries_do_not_carry_events() -> None:
    harness = GameHarness(started_config("auction"))

    snapshot = asyncio.run(harness.use_cases.auction.start())
    current = asyncio.run(GameNightQueryUseCase(harness.uow).get_current())

    assert snapshot is not None and snapshot.events
    assert current.events == ()
    assert current.revision > snapshot.revision
