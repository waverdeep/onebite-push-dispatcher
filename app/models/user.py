from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import (
    PG_UUID,
    UUID,
    Base,
    CIText,
    TZDateTime,
    created_at_col,
    uuid_fk,
    uuid_pk,
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_nickname_pattern",
            "nickname",
            postgresql_ops={"nickname": "text_pattern_ops"},
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(CIText(), unique=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    nickname: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    session_version: Mapped[int] = mapped_column(
        server_default=text("1"), nullable=False
    )
    # Admin (back-office) access. No UI sets this — bootstrap the first admin via
    # scripts.grant_admin. Gated server-side by deps.get_admin_user.
    is_admin: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()
    last_login_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    daily_push_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    # Hour (0-23, KST) the daily reminder is sent. Adapts to the user's actual
    # solve time (see notifications.adaptive); 13 is the cold-start default.
    daily_push_hour: Mapped[int] = mapped_column(
        SmallInteger, server_default=text("13"), nullable=False
    )
    # When true the reminder hour is learned from solve times; the user pinning a
    # fixed hour in settings flips this to false and learning stops.
    daily_push_hour_auto: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    daily_domain_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("domains.id"),
        server_default=text("'cs'"),
        nullable=False,
    )
    friend_request_push: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    weekly_summary_push: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    timezone: Mapped[str] = mapped_column(
        String, server_default=text("'Asia/Seoul'"), nullable=False
    )
    locale: Mapped[str] = mapped_column(
        String, server_default=text("'ko'"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=text("now()"), nullable=False
    )
    # True once the user has actively chosen a daily domain (see patch_settings).
    # New signups start false → the web client gates first-run onboarding on it.
    onboarded: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )


class UserCompanyMembership(Base):
    __tablename__ = "user_company_memberships"
    __table_args__ = (
        Index("ix_ucm_user_active", "user_id", "is_active"),
        Index("ix_ucm_company_active", "company_id", "is_active"),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    company_id: Mapped[UUID] = uuid_fk("companies.id", ondelete="CASCADE")
    verified_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()


__all__ = ["User", "UserSettings", "UserCompanyMembership"]
