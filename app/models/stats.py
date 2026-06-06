from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import UUID, Base, TZDateTime, uuid_fk, uuid_pk

STREAK_EVENT_TYPES = ("completed", "protected", "broken")


class UserStats(Base):
    __tablename__ = "user_stats"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    total_score: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0"), nullable=False
    )
    daily_solved: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    correct_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default=text("0"), nullable=False
    )
    current_streak: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    longest_streak: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    last_daily_date: Mapped[date | None] = mapped_column(Date)
    streak_protection_used_at: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=text("now()"), nullable=False
    )


class StreakEvent(Base):
    __tablename__ = "streak_events"
    __table_args__ = (
        CheckConstraint(
            "type IN ('completed', 'protected', 'broken')",
            name="ck_streak_events_type",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)


class Badge(Base):
    __tablename__ = "badges"

    # slug-style varchar PK (e.g. "streak_7")
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon_url: Mapped[str] = mapped_column(Text, nullable=False)


class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    badge_id: Mapped[str] = mapped_column(
        String, ForeignKey("badges.id"), primary_key=True
    )
    earned_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=text("now()"), nullable=False
    )


__all__ = [
    "UserStats",
    "StreakEvent",
    "Badge",
    "UserBadge",
]
