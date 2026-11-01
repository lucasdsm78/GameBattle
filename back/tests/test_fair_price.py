from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.game_night.game_config_presenter import present_game_config
from application.shared.snapshot import ClientRole
from domain.fair_price.events import PriceHintGiven, PriceTurnEnded, PriceTurnStarted
from domain.fair_price.models.fair_price_state import FAIR_PRICE_TURN_MS
from domain.fair_price.models.price_item import PriceResult
from domain.fair_price.services.fair_price_catalog import (
    PRICE_BANDS,
    PRICE_ITEMS_BY_ID,
    pick_round_items,
)
from domain.shared.services.scoring import TIE_LABEL
from exceptions import CommandNotAllowedError, InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from interface.api.media import MEDIA_DIR
from interface.api.media import router as media_router
from interface.security import SecurityHeadersMiddleware
from support import GameHarness, started_config

TEAMS = ["Rouges", "Bleus", "Verts"]
START_MS = 1_000


def _ready(teams: list[str] | None = None):
    return started_config("fair_price", teams=teams or TEAMS).pull_events()[0]


def _game(config):
    return config.session.fair_price


def _play_turn(config, *, found_after_ms: int | None, hints: int = 0, start_ms: int = START_MS):
    """Joue le tour de l'équipe courante : `hints` indices, puis trouvé après `found_after_ms` (ou temps écoulé)."""
    current = config.start_fair_price_turn(start_ms)
    for index in range(hints):
        current = current.give_fair_price_hint("plus" if index % 2 else "moins", index, start_ms + 1)
    if found_after_ms is None:
        return current.expire_due_deadline(start_ms + FAIR_PRICE_TURN_MS)
    return current.mark_fair_price_found(hints, start_ms + found_after_ms)


def _produced(before, after):
    return after.pending_events[len(before.pending_events):]


def test_each_team_gets_a_different_object_from_the_same_price_band() -> None:
    game = _game(_ready())

    assert game.phase == "ready" and sorted(game.turn_order) == sorted(TEAMS)
    items = [PRICE_ITEMS_BY_ID[item_id] for item_id in game.item_ids]
    band = next(band for band in PRICE_BANDS if band.id == game.band_id)
    assert len({item.id for item in items}) == len(TEAMS) and all(item in band.items for item in items)
    assert len({item.price for item in items}) == len(TEAMS)  # personne ne peut reprendre le prix d'une autre équipe
    assert game.current_team == game.turn_order[0]


def test_a_turn_runs_on_a_server_timer_with_plus_and_minus_hints() -> None:
    running = _ready().start_fair_price_turn(START_MS)
    game = _game(running)
    assert game.phase == "running" and game.deadline_ms == START_MS + FAIR_PRICE_TURN_MS

    hinted = running.give_fair_price_hint("plus", 0, START_MS + 500)
    assert _game(hinted).hint == "plus" and _game(hinted).proposals == 1
    with pytest.raises(InvalidGameConfigError, match="plus"):
        running.give_fair_price_hint("autour", 0, START_MS + 500)


def test_presenter_decisions_are_idempotent() -> None:
    hinted = _ready().start_fair_price_turn(START_MS).give_fair_price_hint("moins", 0, START_MS + 10)

    assert hinted.give_fair_price_hint("moins", 0, START_MS + 11) is hinted
    assert hinted.mark_fair_price_found(0, START_MS + 12) is hinted


def test_finding_the_price_records_the_time_and_passes_to_the_next_team() -> None:
    config = _ready()
    first_team = _game(config).current_team
    after = _play_turn(config, found_after_ms=12_340, hints=4)
    game = _game(after)

    assert game.phase == "ready" and game.current_team == game.turn_order[1]
    assert game.results == [PriceResult(first_team, game.item_ids[0], found=True, elapsed_ms=12_340, proposals=5)]
    assert game.hint == "" and game.proposals == 0


def test_a_team_that_runs_out_of_time_has_not_found() -> None:
    game = _game(_play_turn(_ready(), found_after_ms=None, hints=2))

    assert game.results[0].found is False and game.results[0].elapsed_ms == FAIR_PRICE_TURN_MS


def test_the_fastest_team_wins_the_manche() -> None:
    config = _ready()
    for elapsed in (20_000, 8_500, None):
        config = _play_turn(config, found_after_ms=elapsed)
    game = _game(config)

    assert game.phase == "finished" and game.winner_team == game.turn_order[1]
    assert config.session.manche_winner == game.turn_order[1]


def test_nobody_finding_the_price_is_a_tie() -> None:
    config = _ready(["Rouges", "Bleus"])
    for _ in range(2):
        config = _play_turn(config, found_after_ms=None)

    assert _game(config).winner_team == TIE_LABEL


def test_the_public_screen_sees_the_object_only_once_the_timer_runs_and_never_its_price() -> None:
    ready = _ready()
    controller, display = present_game_config(ready)
    item = PRICE_ITEMS_BY_ID[_game(ready).item_ids[0]]
    assert controller["session"]["fair_price"]["current_item"]["price"] == item.price
    assert display["session"]["fair_price"]["current_item"] is None
    assert "item_ids" not in controller["session"]["fair_price"] and "item_ids" not in display["session"]["fair_price"]

    running = ready.start_fair_price_turn(START_MS)
    shown = present_game_config(running)[1]["session"]["fair_price"]["current_item"]
    assert shown == {"id": item.id, "name": item.name, "image": item.image, "price": None, "credit": item.credit}

    finished_turn = present_game_config(running.mark_fair_price_found(0, START_MS + 5_000))[1]["session"]["fair_price"]
    assert finished_turn["results"][0]["item"]["price"] == item.price  # révélé une fois le tour terminé


def test_domain_events_never_leak_the_price_during_the_turn() -> None:
    ready = _ready()
    running = ready.start_fair_price_turn(START_MS)
    hinted = running.give_fair_price_hint("plus", 0, START_MS + 100)
    found = hinted.mark_fair_price_found(1, START_MS + 9_000)
    team, item = _game(ready).current_team, PRICE_ITEMS_BY_ID[_game(ready).item_ids[0]]

    assert _produced(ready, running) == (PriceTurnStarted(team, item.name),)
    assert _produced(running, hinted) == (PriceHintGiven(team, "plus"),)
    assert _produced(hinted, found) == (PriceTurnEnded(team, item.price, found=True, elapsed_ms=9_000),)
    assert str(item.price) not in repr(_produced(ready, hinted))


def test_persistence_round_trip() -> None:
    config = _play_turn(_ready(), found_after_ms=4_000, hints=3)

    assert game_config_from_payload(game_config_to_payload(config)).session.fair_price == _game(config)


def _with_retired_items(config, **changes):
    payload = game_config_to_payload(config)
    fair_price = payload["session"]["fair_price"]
    fair_price.update(item_ids=["bicycle", "violin", "telescope"][: len(fair_price["item_ids"])], **changes)
    return payload


def test_a_saved_manche_whose_objects_left_the_catalog_is_redrawn_instead_of_breaking_the_load() -> None:
    running = _ready().start_fair_price_turn(START_MS)
    payload = _with_retired_items(running, results=[])

    game = _game(game_config_from_payload(payload))
    assert game.phase == "ready" and game.results == [] and sorted(game.turn_order) == sorted(TEAMS)
    assert all(item_id in PRICE_ITEMS_BY_ID for item_id in game.item_ids)


def test_a_finished_manche_with_retired_objects_keeps_its_winner_in_the_session() -> None:
    config = _ready()
    for elapsed in (20_000, 8_500, None):
        config = _play_turn(config, found_after_ms=elapsed)
    payload = _with_retired_items(config, results=[])

    loaded = game_config_from_payload(payload)
    assert _game(loaded).phase == "idle" and loaded.session.manche_winner == _game(config).winner_team


def test_tampered_states_are_rejected() -> None:
    config = _play_turn(_ready(), found_after_ms=4_000)
    game = _game(config)
    other_band = next(band for band in PRICE_BANDS if band.id != game.band_id)

    for tampered, message in (
        (replace(game, item_ids=[other_band.items[0].id, *game.item_ids[1:]]), "objets"),
        (replace(game, item_ids=[game.item_ids[0]] * len(TEAMS)), "objets"),
        (replace(game, results=[replace(game.results[0], elapsed_ms=FAIR_PRICE_TURN_MS + 1)]), "temps"),
        (replace(game, phase="finished"), "fin"),
        (replace(game, hint="peut-être"), "indice"),
    ):
        with pytest.raises(InvalidGameConfigError, match=message):
            config._replace_session(fair_price=tampered).validate()


def test_only_the_controller_drives_the_game() -> None:
    harness = GameHarness(_ready(), now_ms=START_MS)

    with pytest.raises(CommandNotAllowedError, match="lecture seule"):
        harness.run("fair-price.start-turn", role=ClientRole.DISPLAY)
    harness.run("fair-price.start-turn")
    snapshot = harness.run("fair-price.hint", {"direction": "moins", "proposals": 0})
    assert [event["type"] for event in snapshot.events] == ["fair_price.hint_given"]


def test_the_deadline_worker_ends_a_turn_that_runs_out_of_time() -> None:
    clock = {"now": START_MS}
    harness = GameHarness(_ready().start_fair_price_turn(START_MS), now_ms=lambda: clock["now"])

    clock["now"] = START_MS + FAIR_PRICE_TURN_MS
    snapshot = asyncio.run(harness.use_cases.game_night.expire_due_deadlines())
    assert snapshot is not None and _game(harness.config).results[0].found is False


def test_catalog_bands_are_playable_by_six_teams_and_every_image_exists() -> None:
    for band in PRICE_BANDS:
        prices = [item.price for item in band.items]
        assert len(band.items) >= 6 and len(set(prices)) == len(prices) and all(price > 0 for price in prices)
    assert all((MEDIA_DIR / "fair_price" / item.image).is_file() for item in PRICE_ITEMS_BY_ID.values())
    assert len(PRICE_ITEMS_BY_ID) == sum(len(band.items) for band in PRICE_BANDS)

    band, items = pick_round_items(6)
    assert len({item.id for item in items}) == 6 and all(item in band.items for item in items)


def _media_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(media_router)
    return TestClient(app)


@pytest.mark.parametrize(
    ("name", "media_type", "signature"),
    [("renault-clio.jpg", "image/jpeg", b"\xff\xd8\xff"), ("bialetti-moka-express.png", "image/png", b"\x89PNG")],
)
def test_images_are_served_with_cache_and_cross_origin_headers(name: str, media_type: str, signature: bytes) -> None:
    response = _media_client().get(f"/media/fair-price/{name}")

    assert response.status_code == 200 and response.headers["content-type"] == media_type
    assert response.content.startswith(signature)
    assert response.headers["cache-control"] == "public, max-age=604800, immutable"
    assert response.headers["cross-origin-resource-policy"] == "cross-origin"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("name", ["inconnu.jpg", "..%2F..%2Fmain.py", "CREDITS.md", "renault-clio.JPG"])
def test_only_catalog_images_are_served(name: str) -> None:
    assert _media_client().get(f"/media/fair-price/{name}").status_code == 404


def test_every_photo_is_credited_with_its_author_license_and_price_source() -> None:
    credits = (Path(MEDIA_DIR) / "fair_price" / "CREDITS.md").read_text()
    for item in PRICE_ITEMS_BY_ID.values():
        author_and_license = item.credit.removeprefix("Photo : ")
        assert item.credit.startswith("Photo : ") and " · " in author_and_license
        row = next(line for line in credits.splitlines() if line.startswith(f"| `{item.image}` |"))
        assert all(part in row for part in author_and_license.split(" · ")) and "commons.wikimedia.org" in row
    assert {path.name for path in (Path(MEDIA_DIR) / "fair_price").iterdir()} == {
        "CREDITS.md",
        *(item.image for item in PRICE_ITEMS_BY_ID.values()),
    }
