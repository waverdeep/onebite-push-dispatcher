from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import UUID, Base, TZDateTime, created_at_col, uuid_pk

FRIENDSHIP_STATUSES = ("pending", "accepted")


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint(
            "requester_id", "addressee_id", name="uq_friendships_pair"
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted')", name="ck_friendships_status"
        ),
        Index("ix_friendships_addressee_status", "addressee_id", "status"),
        Index("ix_friendships_requester_status", "requester_id", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    requester_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    addressee_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String, server_default=text("'pending'"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()
    accepted_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_blocks_pair"),
        Index("ix_blocks_blocked", "blocked_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    blocker_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    blocked_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = created_at_col()


__all__ = ["Friendship", "Block"]
