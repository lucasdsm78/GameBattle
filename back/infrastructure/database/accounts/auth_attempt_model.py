from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base


class AuthAttemptModel(Base):
    """Compteur d'essais par fenêtre fixe ; `key` est un HMAC (portée + adresse IP ou pseudo), jamais la donnée en clair."""

    __tablename__ = "auth_attempts"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
