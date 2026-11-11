from __future__ import annotations

import ipaddress
import secrets
from pathlib import Path
from typing import Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from infrastructure.constants.environments import LOCAL_ENVIRONMENTS

BASE_DIR = Path(__file__).resolve().parents[1]
IpNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GAMEBATTLE_",
        case_sensitive=False,
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GameBattle API"
    environment: str = Field(default="development", min_length=2, max_length=30)
    allowed_origins: str = "http://localhost:5173,http://localhost:8081"
    controller_token: str = Field(default="change-me-controller", min_length=8)
    display_token: str = Field(default="change-me-display", min_length=8)
    hardware_token: str = Field(default="change-me-hardware", min_length=8)
    database_url: str = Field(default="postgresql+asyncpg://gamebattle:gamebattle@localhost:5432/gamebattle", min_length=1)
    blindtest_playlist_url: str = ""
    docs_enabled: bool = True
    # Origines exactes de l'app joueur (`https://jeu.exemple.fr`), seules autorisées à écrire sur /api/accounts.
    # Vide en développement : on compare alors l'Origin à l'hôte de la requête (proxy Vite, même origine).
    player_origins: str = ""
    # Adresses (ou réseaux CIDR) des reverse proxies de confiance, Caddy en production. `X-Forwarded-For` n'est lu
    # que pour une connexion venant de l'un d'eux ; vide (développement), l'en-tête est ignoré.
    trusted_proxies: str = ""
    # Clé HMAC des compteurs d'essais (`auth_attempts`), propre à cet usage : jamais un jeton d'authentification.
    # Obligatoire dès qu'on est déployé (`openssl rand -hex 32`) ; en local, une clé aléatoire par processus suffit.
    rate_limit_secret: str = ""

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("trusted_proxies")
    @classmethod
    def validate_trusted_proxies(cls, value: str) -> str:
        for entry in filter(None, (part.strip() for part in value.split(","))):
            ipaddress.ip_network(entry, strict=False)  # une adresse invalide arrête le démarrage, pas une requête
        return value

    @field_validator("rate_limit_secret")
    @classmethod
    def validate_rate_limit_secret(cls, value: str) -> str:
        # Un espace ou un retour à la ligne collé par erreur changerait la clé sans que rien ne le signale.
        if any(character.isspace() for character in value):
            raise ValueError("rate_limit_secret ne doit contenir aucun espace : générez-le avec `openssl rand -hex 32`.")
        return value

    @model_validator(mode="after")
    def validate_deployment_secrets(self) -> Settings:
        if not self.is_deployed:
            if not self.rate_limit_secret:
                self.rate_limit_secret = secrets.token_hex(32)
            return self
        where = f"en environnement « {self.environment} »"
        default_tokens = {
            "controller_token": "change-me-controller",
            "display_token": "change-me-display",
            "hardware_token": "change-me-hardware",
        }
        for field_name, default_value in default_tokens.items():
            if getattr(self, field_name) == default_value:
                raise ValueError(f"{field_name} doit être changé {where}.")
        if not self.player_origins_set:
            raise ValueError(f"player_origins doit lister l'origine de l'app joueur {where}.")
        if not self.trusted_proxy_networks:
            raise ValueError(f"trusted_proxies doit désigner le reverse proxy {where} : sinon tous les joueurs partagent son adresse.")
        if len(self.rate_limit_secret) < 32:
            raise ValueError(f"rate_limit_secret doit faire au moins 32 caractères {where}.")
        if self.rate_limit_secret in {self.controller_token, self.display_token, self.hardware_token}:
            raise ValueError("rate_limit_secret doit être un secret dédié, distinct des jetons.")
        return self

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def fastapi_docs_urls(self) -> dict[str, Optional[str]]:
        if self.docs_enabled:
            return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}

    @property
    def player_origins_set(self) -> frozenset[str]:
        return frozenset(origin.strip().rstrip("/") for origin in self.player_origins.split(",") if origin.strip())

    @property
    def trusted_proxy_networks(self) -> tuple[IpNetwork, ...]:
        return tuple(ipaddress.ip_network(entry.strip(), strict=False) for entry in self.trusted_proxies.split(",") if entry.strip())

    @property
    def creates_schema_on_startup(self) -> bool:
        """Une fois déployé, le schéma n'évolue que par les migrations Alembic (`alembic upgrade head`)."""
        return not self.is_deployed

    @property
    def is_deployed(self) -> bool:
        """Staging, recette, production… : tout ce qui n'est pas explicitement local (HTTPS, secrets obligatoires)."""
        return self.environment not in LOCAL_ENVIRONMENTS

    @property
    def is_production(self) -> bool:
        return self.environment in {"prod", "production"}

