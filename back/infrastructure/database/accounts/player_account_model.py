from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base


class PlayerAccountModel(Base):
    __tablename__ = "player_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pseudo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Forme sans casse : l'index unique empêche deux inscriptions simultanées du même pseudo.
    pseudo_key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
