from __future__ import annotations

from typing import get_args

from application.game_config.game_config_models import GameKey
from application.games import ALL_COMMANDS
from domain.game_config.model.games import GAME_STATE_TYPES
from domain.game_config.model.session import GameSession
from domain.game_config.model.settings import SUPPORTED_GAME_KEYS


def test_every_game_is_registered_consistently_across_layers() -> None:
    session_fields = set(GameSession.__dataclass_fields__)

    assert set(GAME_STATE_TYPES) == SUPPORTED_GAME_KEYS == set(get_args(GameKey))
    assert set(GAME_STATE_TYPES) <= session_fields


def test_command_names_are_unique() -> None:
    names = [spec.name for spec in ALL_COMMANDS]

    assert len(names) == len(set(names))


def test_display_can_only_trigger_buzzers_timers_and_spotify_token() -> None:
    display_commands = {spec.name for spec in ALL_COMMANDS if "display" in spec.roles}

    assert display_commands == {
        "blindtest.buzzer",
        "spotify.user-token",
        "stopchrono.start",
        "stopchrono.stop",
        "culture.buzzer",
        "bombe.buzzer",
        "bombe.begin-after-roll",
        "bombe.explode",
        "seven-differences.open",
        "seven-differences.buzzer",
        "auction.buzzer",
    }
