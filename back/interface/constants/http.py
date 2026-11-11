"""Protocole HTTP : cookies de session, en-têtes, méthodes et bornes des requêtes."""

from __future__ import annotations

# Déployé (HTTPS), le préfixe `__Host-` impose au navigateur Secure, Path=/ et aucun Domain : le cookie ne fuit vers aucun sous-domaine.
SESSION_COOKIE_DEPLOYED = "__Host-gb_session"
SESSION_COOKIE_LOCAL = "gb_session"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
CONTROLLER_TOKEN_HEADER = "X-GameBattle-Controller-Token"
HARDWARE_TOKEN_HEADER = "X-GameBattle-Hardware-Token"
MAX_CREDENTIALS_BODY_BYTES = 2_048
UNKNOWN_ADDRESS = "inconnue"
MAX_REPORTED_PEERS = 256
SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (
        b"content-security-policy",
        b"default-src 'self'; connect-src 'self' ws: wss: http: https:; img-src 'self' data:; "
        b"style-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'",
    ),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"cross-origin-resource-policy", b"same-site"),
    (b"cache-control", b"no-store"),
)
