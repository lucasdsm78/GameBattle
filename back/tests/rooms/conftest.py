from __future__ import annotations

from collections.abc import Iterator

import pytest
from room_app_support import RoomApp, running_room_app


@pytest.fixture
def room_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[RoomApp]:
    with running_room_app(monkeypatch) as app:
        yield app
