from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base


class PlayerSessionModel(Base):
    __tablename__ = "player_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Clé étrangère par nom de table : le module comptes ne dépend que de ses propres tables.
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("player_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
