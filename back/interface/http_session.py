from __future__ import annotations

from collections.abc import Mapping
from typing import Optional
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

from interface.constants.http import SAFE_METHODS, SESSION_COOKIE_DEPLOYED, SESSION_COOKIE_LOCAL
from interface.dependencies.container import get_settings

FOREIGN_ORIGIN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origine de la requête refusée.")


def session_cookie_name() -> str:
    return SESSION_COOKIE_DEPLOYED if get_settings().is_deployed else SESSION_COOKIE_LOCAL


def session_token(cookies: Mapping[str, str]) -> Optional[str]:
    """Jeton de session du cookie HttpOnly (requête HTTP ou poignée de main WebSocket)."""
    return cookies.get(session_cookie_name())


def announced_origin(headers: Mapping[str, str]) -> Optional[str]:
    """Origine annoncée par le navigateur : `Origin`, sinon celle du `Referer`. `Origin: null` n'est jamais de confiance."""
    origin = headers.get("origin")
    if origin is not None:
        return None if origin == "null" else origin.rstrip("/")
    referer = urlsplit(headers.get("referer", ""))
    return f"{referer.scheme}://{referer.netloc}" if referer.scheme and referer.netloc else None


def origin_is_trusted(origin: Optional[str], host: Optional[str]) -> bool:
    """L'origine doit figurer dans `player_origins` (obligatoire une fois déployé) ; sans liste, en développement,
    elle doit désigner l'hôte de la requête (proxy Vite, même origine)."""
    if origin is None:
        return False
    allowed = get_settings().player_origins_set
    return origin in allowed if allowed else urlsplit(origin).netloc == host


def require_same_origin(request: Request) -> None:
    """Anti-CSRF en plus de `SameSite=Strict`, avant tout traitement.

    - Une écriture doit annoncer son origine (`Origin` ou `Referer`), et cette origine doit être de confiance.
    - `Sec-Fetch-Site: cross-site` est toujours refusé, lecture comprise.
    L'app joueur envoie bien son origine : sa politique de référent est `same-origin`, pas `no-referrer`
    (qui ferait envoyer `Origin: null`).
    """
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise FOREIGN_ORIGIN
    if request.method not in SAFE_METHODS and not origin_is_trusted(announced_origin(request.headers), request.headers.get("host")):
        raise FOREIGN_ORIGIN
