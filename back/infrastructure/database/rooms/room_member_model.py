from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base


class RoomMemberModel(Base):
    __tablename__ = "room_members"

    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True)
    # Unique : un joueur n'est que dans un salon à la fois, même face à deux entrées simultanées.
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("player_accounts.id", ondelete="CASCADE"), primary_key=True, unique=True
    )
    pseudo: Mapped[str] = mapped_column(String(20), nullable=False)
    team: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
