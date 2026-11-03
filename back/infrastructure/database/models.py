from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base


class GameConfigStateModel(Base):
    __tablename__ = "game_config_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aggregate_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, default="current")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="api")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")



class PlayerAccountModel(Base):
    __tablename__ = "player_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pseudo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Forme sans casse : l'index unique empêche deux inscriptions simultanées du même pseudo.
    pseudo_key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)


class PlayerSessionModel(Base):
    __tablename__ = "player_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("player_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)


class AuthAttemptModel(Base):
    """Compteur d'essais par fenêtre fixe ; `key` est une empreinte (portée + adresse IP ou pseudo)."""

    __tablename__ = "auth_attempts"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
