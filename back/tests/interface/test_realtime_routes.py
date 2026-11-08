from __future__ import annotations

from interface.realtime.routes import ROUTES


def test_websocket_events_are_unique() -> None:
    names = [route.event for route in ROUTES]

    assert len(names) == len(set(names))


def test_display_can_only_trigger_buzzers_timers_and_spotify_token() -> None:
    display_commands = {route.event for route in ROUTES if "display" in route.roles}

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
        "vanishing-word.buzzer",
        "flash-calc.buzzer",
        "right-flag.buzzer",
        "golden-family.buzzer",
    }
