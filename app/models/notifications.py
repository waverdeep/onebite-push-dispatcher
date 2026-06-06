from datetime import datetime

from sqlalchemy import Boolean, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import (
    UUID,
    Base,
    TZDateTime,
    created_at_col,
    uuid_fk,
    uuid_pk,
)


class PushSubscription(Base):
    """A browser Web Push subscription (one row per device/browser that granted
    permission). One user has N subscriptions. `endpoint` is the per-device
    delivery URL and is globally unique — the same browser endpoint belongs to
    at most one user, so re-subscribing under a different account reassigns it
    (upsert on endpoint in the service layer)."""

    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
        # The send loop fetches all of a user's subscriptions by user_id.
        Index("ix_push_subscriptions_user", "user_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    # Web Push encryption keys (subscription.keys.p256dh / .auth).
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()
    # Bumped on each successful delivery; expired endpoints (404/410) are deleted.
    last_used_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class Notification(Base):
    """A persistent in-app notification (the durable counterpart to a — possibly
    missed — push). Every notification event writes a row here even when the user
    has no push subscription, so the notification center stays a complete record
    (the safety net for iOS / permission-denied users)."""

    __tablename__ = "notifications"
    __table_args__ = (
        # List query: a user's notifications newest-first.
        Index("ix_notifications_user_created", "user_id", "created_at"),
        # Partial index keeps the unread-count poll (every 30s, every user) cheap.
        Index(
            "ix_notifications_user_unread",
            "user_id",
            postgresql_where=text("is_read = false"),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    # Free-form (daily_reminder / friend_request / streak / ...). No CheckConstraint
    # on purpose — new types are added often and we don't want a migration each time.
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Where notificationclick / list-item click navigates (e.g. "/friends").
    link: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()


__all__ = ["PushSubscription", "Notification"]
