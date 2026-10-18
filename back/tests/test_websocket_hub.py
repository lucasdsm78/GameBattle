from __future__ import annotations

import asyncio
import json

from application.shared.snapshot import ClientRole
from interface.realtime.hub import ClientChannel, WebSocketHub
from support import GameHarness, started_config


class _RecordingWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(json.loads(text))

    async def close(self, code: int = 1000) -> None:
        pass


async def _drain(channel: ClientChannel) -> None:
    for _ in range(5):
        await asyncio.sleep(0)
    await channel.close()


def test_a_slow_client_skips_intermediate_states_but_never_loses_events() -> None:
    websocket = _RecordingWebSocket()

    async def scenario():
        channel = ClientChannel(websocket, ClientRole.DISPLAY)  # type: ignore[arg-type]
        channel.push_state(1, "game.config.updated", '{"step":1}', ({"type": "buzzer.pressed", "team": "Rouges"},))
        channel.push_state(2, "game.config.updated", '{"step":2}', ({"type": "answer.judged", "team": "Rouges"},))
        await _drain(channel)

    asyncio.run(scenario())

    assert websocket.sent == [
        {
            "type": "game.config.updated",
            "payload": {"step": 2},
            "events": [{"type": "buzzer.pressed", "team": "Rouges"}, {"type": "answer.judged", "team": "Rouges"}],
        }
    ]


def test_an_older_state_never_overwrites_a_newer_one() -> None:
    websocket = _RecordingWebSocket()

    async def scenario():
        channel = ClientChannel(websocket, ClientRole.CONTROLLER)  # type: ignore[arg-type]
        channel.push_state(5, "game.config.updated", '{"step":5}')
        channel.push_state(4, "game.config.snapshot", '{"step":4}')
        await _drain(channel)

    asyncio.run(scenario())

    assert [message["payload"] for message in websocket.sent] == [{"step": 5}]


def test_direct_replies_are_sent_before_the_pending_state() -> None:
    websocket = _RecordingWebSocket()

    async def scenario():
        channel = ClientChannel(websocket, ClientRole.CONTROLLER)  # type: ignore[arg-type]
        channel.push_state(1, "game.config.updated", "{}")
        channel.push_reply({"type": "error", "detail": "Refusé"})
        await _drain(channel)

    asyncio.run(scenario())

    assert [message["type"] for message in websocket.sent] == ["error", "game.config.updated"]


def test_hub_sends_each_role_its_own_view_with_the_same_events() -> None:
    harness = GameHarness(started_config("forbidden_word").pull_events()[0], now_ms=1_000)
    snapshot = asyncio.run(harness.use_cases.forbidden_word.start_turn())
    assert snapshot is not None
    controller_socket, display_socket = _RecordingWebSocket(), _RecordingWebSocket()

    async def scenario():
        hub = WebSocketHub()
        controller = hub.connect(controller_socket, ClientRole.CONTROLLER)  # type: ignore[arg-type]
        display = hub.connect(display_socket, ClientRole.DISPLAY)  # type: ignore[arg-type]
        hub.publish(snapshot)
        for _ in range(5):
            await asyncio.sleep(0)
        await hub.disconnect(controller)
        await hub.disconnect(display)

    asyncio.run(scenario())

    controller_message, display_message = controller_socket.sent[0], display_socket.sent[0]
    assert controller_message["payload"]["session"]["forbidden_word"]["current_card"] is not None
    assert display_message["payload"]["session"]["forbidden_word"]["current_card"] is None
    assert controller_message["events"] == display_message["events"] == [dict(event) for event in snapshot.events]
