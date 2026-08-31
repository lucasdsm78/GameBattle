from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from infrastructure.spotify.spotify_playlist_service import SpotifyPlaylistImportResult, SpotifyPlaylistTrackData

TEST_DB_PATH = Path(tempfile.gettempdir()) / "gamebattle_test.db"

os.environ["GAMEBATTLE_DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["GAMEBATTLE_CONTROLLER_TOKEN"] = "controller-test-token"
os.environ["GAMEBATTLE_DISPLAY_TOKEN"] = "display-test-token"
os.environ["GAMEBATTLE_ALLOWED_ORIGINS"] = "http://localhost:5173,http://localhost:8081"
os.environ["GAMEBATTLE_SPOTIFY_CLIENT_ID"] = "spotify-client-id-test"
os.environ["GAMEBATTLE_SPOTIFY_CLIENT_SECRET"] = "spotify-client-secret-test"
os.environ["GAMEBATTLE_HARDWARE_TOKEN"] = "hardware-test-token"

from main import app  # noqa: E402


def setup_function() -> None:
    if not TEST_DB_PATH.exists():
        return

    connection = sqlite3.connect(TEST_DB_PATH)
    try:
        connection.execute("DELETE FROM game_config_state")
        connection.commit()
    except sqlite3.OperationalError:
        connection.rollback()
    finally:
        connection.close()


def _payload(title: str = "Soirée des champions") -> dict:
    return {
        "settings": {
            "game_title": title,
            "random_round_order": True,
            "teams": ["Rouges", "Bleus"],
            "buzzer_keys": ["a", "l"],
        },
        "status": "ready",
        "games": [
            {
                "game_key": "blindtest",
                "label": "Blindtest",
                "enabled": True,
                "round_count": 1,
            }
        ],
        "rounds": [
            {
                "id": "blindtest-a",
                "label": "Blindtest aléatoire",
                "game_key": "blindtest",
                "planned_track_count": 10,
                "buzzer_enabled": True,
            }
        ],
    }


def _playlist_payload() -> dict:
    seed_tracks = [
        ("Blinding Lights", "The Weeknd"),
        ("One More Time", "Daft Punk"),
        ("Bad Guy", "Billie Eilish"),
        ("Get Lucky", "Daft Punk"),
        ("Levitating", "Dua Lipa"),
        ("Flowers", "Miley Cyrus"),
        ("Uptown Funk", "Mark Ronson"),
        ("Rolling in the Deep", "Adele"),
        ("Can’t Stop", "Red Hot Chili Peppers"),
        ("Freed from Desire", "Gala"),
    ]
    return {
        "tracks": [
            {
                "title": title,
                "artist": artist,
                "preview_url": f"https://example.com/audio{index}.mp3",
                "artwork_url": f"https://example.com/art{index}.jpg",
            }
            for index, (title, artist) in enumerate(seed_tracks, start=1)
        ]
    }


def _bombe_payload() -> dict:
    payload = _payload("Soirée La Bombe")
    payload["settings"]["total_rounds"] = 1
    payload["games"] = [
        {
            "game_key": "bombe",
            "label": "La Bombe",
            "enabled": True,
            "round_count": 0,
        }
    ]
    payload["rounds"] = []
    return payload


def _spotify_tracks(prefix: str = "spotify-track") -> list[SpotifyPlaylistTrackData]:
    return [
        SpotifyPlaylistTrackData(
            track_id=f"{prefix}-{index}",
            title=f"Track {index}",
            artist=f"Artist {index}",
            preview_url="" if index == 1 else f"https://p.scdn.co/mp3-preview/{prefix}-{index}",
            artwork_url=f"https://i.scdn.co/image/{prefix}-{index}",
        )
        for index in range(1, 11)
    ]


def test_get_default_config() -> None:
    with TestClient(app) as client:
        response = client.get("/api/game-config/current")
        assert response.status_code == 200
        body = response.json()
        assert body["settings"]["game_title"] == "GameBattle Night"
        assert body["settings"]["buzzer_keys"] == ["1", "2"]
        assert body["summary"]["round_count"] >= 1
        assert body["games"][0]["game_key"] == "blindtest"


def test_replace_config_via_http() -> None:
    with TestClient(app) as client:
        response = client.put("/api/game-config/current", json=_payload())
        assert response.status_code == 200
        body = response.json()
        assert body["settings"]["game_title"] == "Soirée des champions"
        assert body["summary"]["round_count"] == 1
        assert body["settings"]["teams"] == ["Rouges", "Bleus"]
        assert body["settings"]["buzzer_keys"] == ["a", "l"]


def test_launch_game_and_drive_blindtest_via_http() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())

        launch_response = client.post("/api/game-config/launch")
        assert launch_response.status_code == 200
        launched = launch_response.json()
        assert launched["status"] == "live"
        assert launched["session"]["active_round"]["game_key"] == "blindtest"

        playlist_response = client.put("/api/game-config/blindtest/playlist", json=_playlist_payload())
        assert playlist_response.status_code == 200
        playlist_body = playlist_response.json()
        assert playlist_body["session"]["blindtest"]["total_tracks"] == 10
        assert playlist_body["session"]["blindtest"]["tracks_remaining"] == 10
        assert playlist_body["session"]["blindtest"]["current_track"]["title"]

        buzzer_response = client.post("/api/game-config/blindtest/buzzer", json={"team": "Rouges"})
        assert buzzer_response.status_code == 200
        assert buzzer_response.json()["session"]["blindtest"]["current_buzzer_team"] == "Rouges"

        answer_response = client.post("/api/game-config/blindtest/answer", json={"is_correct": True})
        assert answer_response.status_code == 200
        answer_body = answer_response.json()
        assert answer_body["session"]["blindtest"]["scores"]["Rouges"] == 1
        assert answer_body["session"]["blindtest"]["revealed"] is True

        next_response = client.post("/api/game-config/blindtest/next-track")
        assert next_response.status_code == 200
        next_body = next_response.json()
        assert next_body["session"]["blindtest"]["current_track_index"] == 2
        assert next_body["session"]["blindtest"]["tracks_remaining"] == 9
        assert next_body["session"]["blindtest"]["current_track"]["artist"]


def test_import_spotify_playlist_via_http() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())
        client.post("/api/game-config/launch")

        spotify_result = SpotifyPlaylistImportResult(
            playlist_id="37i9dQZF1DXcBWIGoYBM5M",
            playlist_name="Today's Top Hits",
            playlist_url="https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            tracks=_spotify_tracks("top-hits"),
        )

        with patch(
            "infrastructure.spotify.spotify_playlist_service.SpotifyPlaylistService.import_playlist",
            new=AsyncMock(return_value=spotify_result),
        ):
            response = client.post(
                "/api/game-config/blindtest/playlist/import-spotify",
                json={"playlist_url": spotify_result.playlist_url},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["session"]["blindtest"]["playlist_provider"] == "spotify"
        assert body["session"]["blindtest"]["playlist_name"] == "Today's Top Hits"
        assert body["session"]["blindtest"]["playlist_source_url"] == spotify_result.playlist_url
        assert body["session"]["blindtest"]["total_tracks"] == 10
        assert len(body["session"]["blindtest"]["tracks"]) == 10
        assert body["session"]["blindtest"]["current_track"]["title"].startswith("Track ")


def test_first_buzzer_is_locked_until_answer() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())
        client.post("/api/game-config/launch")
        client.put("/api/game-config/blindtest/playlist", json=_playlist_payload())

        first_buzz_response = client.post("/api/game-config/blindtest/buzzer", json={"team": "Rouges"})
        assert first_buzz_response.status_code == 200
        assert first_buzz_response.json()["session"]["blindtest"]["current_buzzer_team"] == "Rouges"

        second_buzz_response = client.post("/api/game-config/blindtest/buzzer", json={"team": "Bleus"})
        assert second_buzz_response.status_code == 400
        assert second_buzz_response.json()["detail"] == "Un buzz est déjà en attente de validation."

        reset_response = client.post("/api/game-config/blindtest/answer", json={"is_correct": False})
        assert reset_response.status_code == 200
        assert reset_response.json()["session"]["blindtest"]["current_buzzer_team"] is None

        third_buzz_response = client.post("/api/game-config/blindtest/buzzer", json={"team": "Bleus"})
        assert third_buzz_response.status_code == 200
        assert third_buzz_response.json()["session"]["blindtest"]["current_buzzer_team"] == "Bleus"


def test_playback_sync_via_http() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())
        client.post("/api/game-config/launch")
        client.put("/api/game-config/blindtest/playlist", json=_playlist_payload())

        play_response = client.post("/api/game-config/blindtest/playback/control", json={"action": "play"})
        assert play_response.status_code == 200
        assert play_response.json()["session"]["blindtest"]["playback_state"] == "playing"

        sync_response = client.post(
            "/api/game-config/blindtest/playback/sync",
            json={
                "track_id": play_response.json()["session"]["blindtest"]["current_track"]["track_id"],
                "playback_state": "playing",
                "position_ms": 12500,
                "duration_ms": 30000,
            },
        )
        assert sync_response.status_code == 200
        body = sync_response.json()
        assert body["session"]["blindtest"]["playback_position_ms"] == 12500
        assert body["session"]["blindtest"]["playback_duration_ms"] == 30000


def test_hardware_buzzer_event_requires_token() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())
        client.post("/api/game-config/launch")
        client.put("/api/game-config/blindtest/playlist", json=_playlist_payload())

        unauthorized = client.post("/api/hardware/buzzer-events", json={"team": "Rouges"})
        assert unauthorized.status_code == 401

        authorized = client.post(
            "/api/hardware/buzzer-events",
            json={"team": "Rouges"},
            headers={"X-GameBattle-Hardware-Token": "hardware-test-token"},
        )
        assert authorized.status_code == 200
        assert authorized.json()["session"]["blindtest"]["current_buzzer_team"] == "Rouges"


def test_websocket_broadcast_from_controller_to_display() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/game-config?client_type=display&token=display-test-token") as display_ws:
            first = display_ws.receive_json()
            assert first["type"] == "game.config.snapshot"

            with client.websocket_connect("/ws/game-config?client_type=controller&token=controller-test-token") as controller_ws:
                snapshot = controller_ws.receive_json()
                assert snapshot["type"] == "game.config.snapshot"

                controller_ws.send_json({"type": "game.config.replace", "payload": _payload("Battle Royale")})
                updated_for_controller = controller_ws.receive_json()
                updated_for_display = display_ws.receive_json()

                assert updated_for_controller["type"] == "game.config.updated"
                assert updated_for_display["type"] == "game.config.updated"
                assert updated_for_display["payload"]["settings"]["game_title"] == "Battle Royale"


def test_websocket_blindtest_flow() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())
        with client.websocket_connect("/ws/game-config?client_type=display&token=display-test-token") as display_ws:
            display_ws.receive_json()

            with client.websocket_connect("/ws/game-config?client_type=controller&token=controller-test-token") as controller_ws:
                controller_ws.receive_json()
                controller_ws.send_json({"type": "game.config.launch"})
                launch_controller = controller_ws.receive_json()
                launch_display = display_ws.receive_json()
                assert launch_controller["payload"]["status"] == "live"
                assert launch_display["payload"]["session"]["active_round"]["game_key"] == "blindtest"

                controller_ws.send_json({"type": "blindtest.playlist.load", "payload": _playlist_payload()})
                playlist_controller = controller_ws.receive_json()
                playlist_display = display_ws.receive_json()
                assert playlist_controller["payload"]["session"]["blindtest"]["current_track"]["title"]
                assert len(playlist_controller["payload"]["session"]["blindtest"]["tracks"]) == 10
                assert playlist_display["payload"]["session"]["blindtest"]["total_tracks"] == 10
                assert playlist_display["payload"]["session"]["blindtest"]["current_track"]["title"] == "Titre masqué"
                assert playlist_display["payload"]["session"]["blindtest"]["current_track"]["artwork_url"] == ""
                assert playlist_display["payload"]["session"]["blindtest"]["tracks"] == []

                controller_ws.send_json({"type": "blindtest.buzzer", "payload": {"team": "Bleus"}})
                buzzer_display = display_ws.receive_json()
                controller_ws.receive_json()
                assert buzzer_display["payload"]["session"]["blindtest"]["current_buzzer_team"] == "Bleus"


def test_websocket_spotify_import_broadcast() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())
        with client.websocket_connect("/ws/game-config?client_type=display&token=display-test-token") as display_ws:
            display_ws.receive_json()

            with client.websocket_connect("/ws/game-config?client_type=controller&token=controller-test-token") as controller_ws:
                controller_ws.receive_json()
                controller_ws.send_json({"type": "game.config.launch"})
                controller_ws.receive_json()
                display_ws.receive_json()

                spotify_result = SpotifyPlaylistImportResult(
                    playlist_id="37i9dQZF1DX0XUsuxWHRQd",
                    playlist_name="RapCaviar",
                    playlist_url="https://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd",
                    tracks=_spotify_tracks("rapcaviar"),
                )

                with patch(
                    "infrastructure.spotify.spotify_playlist_service.SpotifyPlaylistService.import_playlist",
                    new=AsyncMock(return_value=spotify_result),
                ):
                    controller_ws.send_json(
                        {
                            "type": "blindtest.playlist.import-spotify",
                            "payload": {"playlist_url": spotify_result.playlist_url},
                        }
                    )
                    updated_for_controller = controller_ws.receive_json()
                    updated_for_display = display_ws.receive_json()

                assert updated_for_controller["payload"]["session"]["blindtest"]["playlist_provider"] == "spotify"
                assert updated_for_display["payload"]["session"]["blindtest"]["playlist_name"] == "RapCaviar"
                assert updated_for_display["payload"]["session"]["blindtest"]["current_track"]["artist"] == "Artiste masqué"
                assert updated_for_display["payload"]["session"]["blindtest"]["current_track"]["artwork_url"] == ""
                assert updated_for_display["payload"]["session"]["blindtest"]["tracks"] == []


def test_display_client_cannot_write() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/game-config?client_type=display&token=display-test-token") as display_ws:
            display_ws.receive_json()
            display_ws.send_json({"type": "game.config.replace", "payload": _payload()})
            message = display_ws.receive_json()
            assert message["type"] == "error"


def test_websocket_bombe_flow_accepts_and_broadcasts_hardware_buzzer() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_bombe_payload())
        with client.websocket_connect("/ws/game-config?client_type=display&token=display-test-token") as display_ws:
            display_ws.receive_json()

            with client.websocket_connect("/ws/game-config?client_type=controller&token=controller-test-token") as controller_ws:
                controller_ws.receive_json()
                controller_ws.send_json({"type": "game.config.validate-and-launch", "payload": _bombe_payload()})
                launched_controller = controller_ws.receive_json()
                launch_display = display_ws.receive_json()
                assert launched_controller["payload"]["session"]["active_round"]["game_key"] == "bombe"
                assert launch_display["payload"]["session"]["active_round"]["game_key"] == "bombe"

                controller_ws.send_json({"type": "bombe.start"})
                started_controller = controller_ws.receive_json()
                started_display = display_ws.receive_json()
                bombe = started_controller["payload"]["session"]["bombe"]
                current_team = started_controller["payload"]["settings"]["teams"][bombe["current_team_index"]]
                assert bombe["phase"] == "awaiting_roll"
                assert started_display["payload"]["session"]["bombe"]["sound"] == bombe["sound"]

                roll_response = client.post(
                    "/api/hardware/buzzer-events",
                    json={"team": current_team},
                    headers={"X-GameBattle-Hardware-Token": "hardware-test-token"},
                )
                roll_controller = controller_ws.receive_json()
                roll_display = display_ws.receive_json()

                assert roll_response.status_code == 200
                assert roll_response.json()["session"]["bombe"]["phase"] == "rolling"
                assert roll_controller["payload"]["session"]["bombe"]["phase"] == "rolling"
                assert roll_display["payload"]["session"]["bombe"]["die_result"] == ""

                reveal_at = roll_response.json()["session"]["bombe"]["die_reveal_at_ms"]
                with patch(
                    "application.bombe.bombe_command_usecase.BombeCommandUseCase._now_ms",
                    return_value=reveal_at,
                ):
                    controller_ws.send_json({"type": "bombe.begin-after-roll"})
                    running_controller = controller_ws.receive_json()
                    running_display = display_ws.receive_json()

                running_bombe = running_controller["payload"]["session"]["bombe"]
                assert running_bombe["phase"] == "running"
                assert running_bombe["deadline_at_ms"] > running_bombe["started_at_ms"]
                assert running_display["payload"]["session"]["bombe"]["die_result"] in {"TIC", "TAC", "BOUM"}

                hardware_response = client.post(
                    "/api/hardware/buzzer-events",
                    json={"team": current_team},
                    headers={"X-GameBattle-Hardware-Token": "hardware-test-token"},
                )
                hardware_controller = controller_ws.receive_json()
                hardware_display = display_ws.receive_json()

                assert hardware_response.status_code == 200
                next_index = hardware_response.json()["session"]["bombe"]["current_team_index"]
                assert next_index != bombe["current_team_index"]
                assert hardware_controller["payload"]["session"]["bombe"]["current_team_index"] == next_index
                assert hardware_display["payload"]["session"]["bombe"]["current_team_index"] == next_index


def test_atomic_validation_failure_does_not_launch_previous_config() -> None:
    with TestClient(app) as client:
        client.put("/api/game-config/current", json=_payload())
        invalid_payload = _bombe_payload()
        invalid_payload["games"][0]["enabled"] = False

        with client.websocket_connect("/ws/game-config?client_type=controller&token=controller-test-token") as controller_ws:
            controller_ws.receive_json()
            controller_ws.send_json({"type": "game.config.validate-and-launch", "payload": invalid_payload})
            error = controller_ws.receive_json()

        current = client.get("/api/game-config/current").json()
        assert error["type"] == "error"
        assert current["status"] == "ready"
        assert current["session"]["active_round"] is None
        assert [(game["game_key"], game["enabled"]) for game in current["games"]] == [("blindtest", True)]

