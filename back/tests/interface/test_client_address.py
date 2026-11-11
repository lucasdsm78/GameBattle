from __future__ import annotations

import ipaddress

import pytest
from pydantic import ValidationError

from infrastructure.config import Settings
from interface.client_address import resolve_client_address
from interface.constants.http import UNKNOWN_ADDRESS

CADDY = [ipaddress.ip_network("172.30.0.10/32")]
PROXIES = [ipaddress.ip_network("172.30.0.0/24"), ipaddress.ip_network("10.0.0.0/8")]


def test_without_trusted_proxies_the_header_is_ignored() -> None:
    assert resolve_client_address("203.0.113.7", "198.51.100.1", []) == "203.0.113.7"


def test_a_client_cannot_forge_its_address_by_sending_the_header_itself() -> None:
    assert resolve_client_address("203.0.113.7", "1.2.3.4", CADDY) == "203.0.113.7"


def test_behind_the_trusted_proxy_the_player_address_is_used() -> None:
    assert resolve_client_address("172.30.0.10", "198.51.100.1", CADDY) == "198.51.100.1"


def test_only_the_rightmost_untrusted_hop_counts() -> None:
    # « 1.2.3.4 » a été écrit par le client : seul ce que le proxy a ajouté à droite fait foi.
    assert resolve_client_address("172.30.0.10", "1.2.3.4, 198.51.100.1", CADDY) == "198.51.100.1"


def test_a_chain_of_trusted_proxies_is_walked_through() -> None:
    assert resolve_client_address("172.30.0.10", "198.51.100.1, 10.1.2.3", PROXIES) == "198.51.100.1"


@pytest.mark.parametrize("header", ["pas-une-adresse", "198.51.100.1, ", "", "172.30.0.10"])
def test_an_unreadable_or_proxy_only_chain_falls_back_to_the_proxy_address(header: str) -> None:
    assert resolve_client_address("172.30.0.10", header, CADDY) == "172.30.0.10"


def test_ipv6_clients_are_supported() -> None:
    assert resolve_client_address("172.30.0.10", "2001:db8::1", CADDY) == "2001:db8::1"


def test_a_missing_peer_is_unknown() -> None:
    assert resolve_client_address(None, "198.51.100.1", CADDY) == UNKNOWN_ADDRESS


def test_trusted_proxies_are_validated_at_startup() -> None:
    assert [str(network) for network in Settings(_env_file=None, trusted_proxies="172.30.0.10, 10.0.0.0/8").trusted_proxy_networks] == [
        "172.30.0.10/32",
        "10.0.0.0/8",
    ]
    with pytest.raises(ValidationError):
        Settings(_env_file=None, trusted_proxies="caddy")
