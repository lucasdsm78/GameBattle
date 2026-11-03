from __future__ import annotations

import ipaddress
from collections.abc import Sequence
from typing import Optional

from fastapi import Request

from infrastructure.config import IpNetwork
from interface.dependencies.container import get_settings

UNKNOWN_ADDRESS = "inconnue"


def _parse(address: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return ipaddress.ip_address(address.strip())
    except ValueError:
        return None


def _trusted(address: Optional[ipaddress.IPv4Address | ipaddress.IPv6Address], proxies: Sequence[IpNetwork]) -> bool:
    return address is not None and any(address in network for network in proxies)


def resolve_client_address(peer: Optional[str], forwarded_for: Optional[str], proxies: Sequence[IpNetwork]) -> str:
    """Adresse du joueur derrière une chaîne de proxies de confiance.

    `X-Forwarded-For` n'est lu que si la connexion vient d'un proxy de confiance ; on le parcourt alors de droite
    à gauche (chaque proxy ajoute à la fin) et on garde la première adresse qui n'est pas un proxy de confiance.
    Tout ce qui est plus à gauche a pu être écrit par le client lui-même : on ne le lit jamais.
    """
    peer_address = _parse(peer or "")
    if peer_address is None:
        return UNKNOWN_ADDRESS
    if not _trusted(peer_address, proxies) or not forwarded_for:
        return str(peer_address)
    for hop in reversed(forwarded_for.split(",")):
        address = _parse(hop)
        if address is None:
            return str(peer_address)  # chaîne illisible : on s'en tient à ce que l'on sait, l'adresse du proxy
        if not _trusted(address, proxies):
            return str(address)
    return str(peer_address)


def client_address(request: Request) -> str:
    """À lancer avec uvicorn `--no-proxy-headers` : `request.client` est alors la vraie connexion TCP."""
    return resolve_client_address(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
        get_settings().trusted_proxy_networks,
    )
