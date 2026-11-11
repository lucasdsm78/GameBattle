from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base
from infrastructure.database.json_document import JsonDocument


class RoomModel(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)  # secret du lien d'invitation
    visibility: Mapped[str] = mapped_column(String(10), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    teams: Mapped[list[str]] = mapped_column(JsonDocument, nullable=False)
    # Clé étrangère par nom de table : le module salons ne dépend pas du code des comptes.
    host_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_accounts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)  # verrou optimiste
    created_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)  # ménage des salons inactifs
