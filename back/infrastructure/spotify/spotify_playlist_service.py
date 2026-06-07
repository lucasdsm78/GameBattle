from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
import re

import httpx

from domain.game_config.exception.game_config_exception import InvalidGameConfigError

_SPOTIFY_PLAYLIST_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")


@dataclass(slots=True)
class SpotifyPlaylistTrackData:
    track_id: str
    title: str
    artist: str
    preview_url: str
    artwork_url: str


@dataclass(slots=True)
class SpotifyPlaylistImportResult:
    playlist_id: str
    playlist_name: str
    playlist_url: str
    tracks: list[SpotifyPlaylistTrackData]


class SpotifyPlaylistService:
    TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"
    API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id.strip()
        self._client_secret = client_secret.strip()
        self._access_token = ""
        self._token_expires_at = 0.0
        # Token utilisateur fourni par l'écran (Web Playback SDK). Requis depuis le changement
        # Spotify de février 2026 : /playlists/{id}/items ne renvoie le contenu que pour les
        # playlists de l'utilisateur authentifié, et Client Credentials ne peut plus lire les pistes.
        self._user_access_token = ""

    def set_user_token(self, token: str) -> None:
        self._user_access_token = (token or "").strip()

    @property
    def has_user_token(self) -> bool:
        return bool(self._user_access_token)

    async def import_playlist(self, playlist_reference: str) -> SpotifyPlaylistImportResult:
        playlist_id = self._extract_playlist_id(playlist_reference)
        if not self._user_access_token:
            raise InvalidGameConfigError(
                "Connecte Spotify sur l'écran avant d'importer : l'API Spotify exige désormais "
                "un token utilisateur pour lire les pistes d'une playlist (changement de février 2026)."
            )
        headers = {"Authorization": f"Bearer {self._user_access_token}"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            playlist_response = await self._send_request(
                client,
                "GET",
                f"{self.API_BASE_URL}/playlists/{playlist_id}",
                headers=headers,
                params={"fields": "name,external_urls.spotify"},
            )
            playlist_payload = playlist_response.json()
            playlist_name = (playlist_payload.get("name") or "Playlist Spotify").strip()
            playlist_url = (playlist_payload.get("external_urls") or {}).get("spotify", "").strip()

            tracks: list[SpotifyPlaylistTrackData] = []
            # Depuis février 2026, /tracks est déprécié au profit de /items.
            next_url = f"{self.API_BASE_URL}/playlists/{playlist_id}/items"
            params: dict[str, object] | None = {"limit": 100, "offset": 0, "market": "FR"}

            while next_url:
                response = await self._send_request(client, "GET", next_url, headers=headers, params=params)
                payload = response.json()
                next_url = payload.get("next") or ""
                params = None

                for item in payload.get("items", []):
                    # Depuis février 2026, l'endpoint /items expose le morceau sous "item"
                    # (l'ancien /tracks utilisait "track"). On gère les deux par sécurité.
                    track_payload = item.get("item") or item.get("track") or {}
                    if not track_payload or track_payload.get("type") != "track" or track_payload.get("is_local"):
                        continue

                    track_id = (track_payload.get("id") or "").strip()
                    title = (track_payload.get("name") or "").strip()
                    artist = ", ".join(
                        artist_payload.get("name", "").strip()
                        for artist_payload in track_payload.get("artists", [])
                        if artist_payload.get("name")
                    ).strip()
                    if not track_id or not title or not artist:
                        continue

                    images = (track_payload.get("album") or {}).get("images") or []
                    artwork_url = images[0].get("url", "").strip() if images else ""
                    tracks.append(
                        SpotifyPlaylistTrackData(
                            track_id=track_id,
                            title=title,
                            artist=artist,
                            preview_url=(track_payload.get("preview_url") or "").strip(),
                            artwork_url=artwork_url,
                        )
                    )

        if not tracks:
            raise InvalidGameConfigError(
                "La playlist Spotify ne contient aucune piste exploitable. Vérifiez qu'elle est publique et non vide."
            )

        return SpotifyPlaylistImportResult(
            playlist_id=playlist_id,
            playlist_name=playlist_name,
            playlist_url=playlist_url,
            tracks=tracks,
        )

    async def _get_access_token(self) -> str:
        if self._access_token and monotonic() < self._token_expires_at - 30:
            return self._access_token

        if not self._client_id or not self._client_secret:
            raise InvalidGameConfigError(
                "Spotify n'est pas configuré. Renseignez GAMEBATTLE_SPOTIFY_CLIENT_ID et GAMEBATTLE_SPOTIFY_CLIENT_SECRET."
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await self._send_request(
                client,
                "POST",
                self.TOKEN_ENDPOINT,
                data={"grant_type": "client_credentials"},
                auth=(self._client_id, self._client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        payload = response.json()
        access_token = (payload.get("access_token") or "").strip()
        expires_in = int(payload.get("expires_in") or 0)
        if not access_token or expires_in <= 0:
            raise InvalidGameConfigError("Spotify a renvoyé un jeton invalide.")

        self._access_token = access_token
        self._token_expires_at = monotonic() + expires_in
        return access_token

    async def _send_request(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise InvalidGameConfigError("Spotify ne répond pas à temps. Réessayez dans quelques secondes.") from exc
        except httpx.HTTPError as exc:
            raise InvalidGameConfigError("Connexion à Spotify impossible.") from exc

        if response.status_code == 401:
            self._access_token = ""
            self._token_expires_at = 0.0
            self._user_access_token = ""
            raise InvalidGameConfigError(
                "Session Spotify de l'écran expirée. Elle se rafraîchit automatiquement : "
                "réessaie l'import dans quelques secondes (ou recharge l'écran)."
            )
        if response.status_code == 403:
            raise InvalidGameConfigError(
                "Spotify autorise uniquement la lecture des pistes de TES propres playlists "
                "(changement de février 2026). Utilise une playlist créée sur le compte connecté à l'écran."
            )
        if response.status_code == 404:
            raise InvalidGameConfigError(
                f"Playlist Spotify introuvable. Vérifiez l'URL ou rendez-la publique. ({self._spotify_error(response)})"
            )
        if response.status_code >= 400:
            raise InvalidGameConfigError(
                f"Spotify a refusé la demande (HTTP {response.status_code} sur {response.request.url.path} : {self._spotify_error(response)})."
            )
        return response

    @staticmethod
    def _spotify_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return (response.text or "").strip()[:200] or "sans détail"
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            return str(error.get("message") or error.get("reason") or error)[:200]
        return str(error or payload)[:200]

    def _extract_playlist_id(self, playlist_reference: str) -> str:
        value = playlist_reference.strip()
        if not value:
            raise InvalidGameConfigError("Veuillez fournir une URL ou un identifiant de playlist Spotify.")

        if value.startswith("spotify:playlist:"):
            candidate = value.rsplit(":", 1)[-1].strip()
        elif "open.spotify.com/playlist/" in value:
            candidate = value.split("open.spotify.com/playlist/", 1)[1].split("?", 1)[0].split("/", 1)[0].strip()
        else:
            candidate = value

        if not _SPOTIFY_PLAYLIST_ID_PATTERN.fullmatch(candidate):
            raise InvalidGameConfigError("Format de playlist Spotify invalide. Utilisez une URL Spotify ou un identifiant de playlist.")
        return candidate

