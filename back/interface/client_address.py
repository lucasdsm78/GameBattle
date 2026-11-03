from __future__ import annotations

import ipaddress
import logging
from collections.abc import Sequence
from typing import Optional

from fastapi import Request

from infrastructure.config import IpNetwork
from interface.dependencies.container import get_settings

logger = logging.getLogger(__name__)
UNKNOWN_ADDRESS = "inconnue"
MAX_REPORTED_PEERS = 256
_reported_peers: set[str] = set()


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
    if not forwarded_for:
        return str(peer_address)
    if not _trusted(peer_address, proxies):
        if proxies:
            _report_untrusted_forwarding(str(peer_address))
        return str(peer_address)
    for hop in reversed(forwarded_for.split(",")):
        address = _parse(hop)
        if address is None:
            return str(peer_address)  # chaîne illisible : on s'en tient à ce que l'on sait, l'adresse du proxy
        if not _trusted(address, proxies):
            return str(address)
    return str(peer_address)


def _report_untrusted_forwarding(peer: str) -> None:
    """Un `X-Forwarded-For` arrivé d'un pair inconnu alors que des proxies sont configurés : soit un client qui
    tente de forger son adresse, soit l'adresse du proxy a changé (réseau Docker modifié). Signalé une fois par pair."""
    if peer in _reported_peers or len(_reported_peers) >= MAX_REPORTED_PEERS:
        return
    _reported_peers.add(peer)
    logger.warning("client_address.untrusted_forwarded_for peer=%s", peer, extra={"peer": peer})


def came_through_trusted_proxy(request: Request) -> bool:
    peer = _parse(request.client.host if request.client else "")
    return _trusted(peer, get_settings().trusted_proxy_networks)


def client_address(request: Request) -> str:
    """À lancer avec uvicorn `--no-proxy-headers` : `request.client` est alors la vraie connexion TCP."""
    return resolve_client_address(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
        get_settings().trusted_proxy_networks,
    )
