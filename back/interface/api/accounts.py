from __future__ import annotations

import json
from typing import Annotated, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import ValidationError

from application.accounts.account_commands import CredentialsCommand
from application.accounts.account_usecase import SignedIn
from domain.accounts.models.player_session import SESSION_TTL_MS
from exceptions import InvalidCommandPayloadError
from interface.client_address import client_address
from interface.dependencies import AccountUseCaseDep
from interface.dependencies.container import get_settings
from interface.schemas.accounts import AccountResponse

MAX_CREDENTIALS_BODY_BYTES = 2_048
# En production, le préfixe `__Host-` impose au navigateur Secure, Path=/ et aucun Domain : le cookie ne fuit vers aucun sous-domaine.
SESSION_COOKIE_PRODUCTION = "__Host-gb_session"
SESSION_COOKIE_DEVELOPMENT = "gb_session"
_TOO_LARGE = HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Requête trop volumineuse.")


def require_same_origin(request: Request) -> None:
    """Anti-CSRF en plus de `SameSite=Strict` : une requête venue d'un autre site est refusée avant tout traitement.

    L'Origin doit figurer dans `player_origins` (obligatoire en production) ; sans liste, en développement, elle
    doit désigner l'hôte de la requête. Les navigateurs récents signalent aussi un appel inter-sites par `Sec-Fetch-Site`.
    """
    origin = request.headers.get("origin")
    allowed = get_settings().player_origins_set
    same_origin = origin is None or (
        origin.rstrip("/") in allowed if allowed else urlsplit(origin).netloc == request.headers.get("host")
    )
    if not same_origin or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origine de la requête refusée.")


async def _read_bounded_body(request: Request, limit: int) -> bytes:
    """Lit le corps par morceaux et s'arrête dès `limit` dépassé, même sans `Content-Length` (envoi en flux)."""
    declared = request.headers.get("content-length")
    if declared is not None and (not declared.isdigit() or int(declared) > limit):
        raise _TOO_LARGE
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise _TOO_LARGE
    return bytes(body)


async def read_credentials(request: Request) -> CredentialsCommand:
    """Lit le corps à la main : l'erreur 422 par défaut de FastAPI renverrait le mot de passe reçu dans sa réponse."""
    body = await _read_bounded_body(request, MAX_CREDENTIALS_BODY_BYTES)
    try:
        return CredentialsCommand.model_validate(json.loads(body))
    except (ValueError, ValidationError):
        raise InvalidCommandPayloadError("Indique un pseudo et un mot de passe.") from None


Credentials = Annotated[CredentialsCommand, Depends(read_credentials)]
router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(require_same_origin)])


def _cookie_name() -> str:
    return SESSION_COOKIE_PRODUCTION if get_settings().is_production else SESSION_COOKIE_DEVELOPMENT


def _session_token(request: Request) -> Optional[str]:
    return request.cookies.get(_cookie_name())


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        _cookie_name(),
        token,
        max_age=SESSION_TTL_MS // 1000,
        httponly=True,  # illisible par le JavaScript de la page : une faille XSS ne vole pas la session
        secure=get_settings().is_production,
        samesite="strict",
        path="/",
    )


def _signed_in(response: Response, signed_in: SignedIn) -> AccountResponse:
    _set_session_cookie(response, signed_in.token)
    return AccountResponse(pseudo=signed_in.account.pseudo)


# La session que ce navigateur avait encore est révoquée dans la même transaction que l'ouverture de la nouvelle.
@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Créer un compte joueur et se connecter")
async def register(credentials: Credentials, request: Request, response: Response, accounts: AccountUseCaseDep) -> AccountResponse:
    return _signed_in(response, await accounts.register(credentials, client_address(request), _session_token(request)))


@router.post("/login", summary="Se connecter avec son pseudo et son mot de passe")
async def login(credentials: Credentials, request: Request, response: Response, accounts: AccountUseCaseDep) -> AccountResponse:
    return _signed_in(response, await accounts.login(credentials, client_address(request), _session_token(request)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Se déconnecter")
async def logout(request: Request, accounts: AccountUseCaseDep) -> Response:
    await accounts.logout(_session_token(request))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(_cookie_name(), path="/", secure=get_settings().is_production, httponly=True, samesite="strict")
    return response


@router.get("/me", summary="Le joueur connecté (prolonge la session d'un joueur actif)")
async def me(request: Request, response: Response, accounts: AccountUseCaseDep) -> AccountResponse:
    token = _session_token(request)
    current = await accounts.current(token)
    if current.renewed_until_ms is not None and token:
        _set_session_cookie(response, token)
    return AccountResponse(pseudo=current.account.pseudo)
