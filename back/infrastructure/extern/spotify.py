from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from exceptions import InvalidGameConfigError

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
    """Lit une playlist avec le token utilisateur poussé par l'écran.

    Depuis février 2026, Spotify ne renvoie les pistes (`/items`) que pour les playlists de
    l'utilisateur authentifié : le flux « client credentials » ne suffit plus.
    """

    API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_access_token = ""
        self._client: Optional[httpx.AsyncClient] = None

    def set_user_token(self, token: str) -> None:
        self._user_access_token = (token or "").strip()

    @property
    def has_user_token(self) -> bool:
        return bool(self._user_access_token)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.API_BASE_URL, timeout=self._timeout_seconds)
        return self._client

    async def import_playlist(self, playlist_reference: str) -> SpotifyPlaylistImportResult:
        playlist_id = self._extract_playlist_id(playlist_reference)
        if not self._user_access_token:
            raise InvalidGameConfigError(
                "Connecte Spotify sur l'écran avant d'importer : l'API Spotify exige désormais "
                "un token utilisateur pour lire les pistes d'une playlist (changement de février 2026)."
            )
        headers = {"Authorization": f"Bearer {self._user_access_token}"}
        playlist_payload = (
            await self._get(f"/playlists/{playlist_id}", headers, {"fields": "name,external_urls.spotify"})
        ).json()

        tracks: list[SpotifyPlaylistTrackData] = []
        next_url: str = f"/playlists/{playlist_id}/items"
        params: Optional[dict[str, Any]] = {"limit": 100, "offset": 0, "market": "FR"}
        while next_url:
            page = (await self._get(next_url, headers, params)).json()
            next_url, params = page.get("next") or "", None
            tracks.extend(track for item in page.get("items", []) if (track := self._parse_track(item)))

        if not tracks:
            raise InvalidGameConfigError(
                "La playlist Spotify ne contient aucune piste exploitable. Vérifiez qu'elle est publique et non vide."
            )
        return SpotifyPlaylistImportResult(
            playlist_id=playlist_id,
            playlist_name=(playlist_payload.get("name") or "Playlist Spotify").strip(),
            playlist_url=(playlist_payload.get("external_urls") or {}).get("spotify", "").strip(),
            tracks=tracks,
        )

    @staticmethod
    def _parse_track(item: dict[str, Any]) -> Optional[SpotifyPlaylistTrackData]:
        # `/items` expose le morceau sous "item" ; l'ancien `/tracks` utilisait "track".
        track = item.get("item") or item.get("track") or {}
        if not track or track.get("type") != "track" or track.get("is_local"):
            return None
        track_id = (track.get("id") or "").strip()
        title = (track.get("name") or "").strip()
        artist = ", ".join(
            artist["name"].strip() for artist in track.get("artists", []) if (artist.get("name") or "").strip()
        )
        if not track_id or not title or not artist:
            return None
        images = (track.get("album") or {}).get("images") or []
        return SpotifyPlaylistTrackData(
            track_id=track_id,
            title=title,
            artist=artist,
            preview_url=(track.get("preview_url") or "").strip(),
            artwork_url=(images[0].get("url") or "").strip() if images else "",
        )

    async def _get(self, url: str, headers: dict[str, str], params: Optional[dict[str, Any]]) -> httpx.Response:
        if url.startswith("http") and not url.startswith(self.API_BASE_URL):
            raise InvalidGameConfigError("Spotify a renvoyé une pagination inattendue.")
        try:
            response = await self._http().get(url, headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise InvalidGameConfigError("Spotify ne répond pas à temps. Réessayez dans quelques secondes.") from exc
        except httpx.HTTPError as exc:
            raise InvalidGameConfigError("Connexion à Spotify impossible.") from exc

        if response.status_code == 401:
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
                f"Spotify a refusé la demande (HTTP {response.status_code} sur {response.request.url.path} : "
                f"{self._spotify_error(response)})."
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

    @staticmethod
    def _extract_playlist_id(playlist_reference: str) -> str:
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
