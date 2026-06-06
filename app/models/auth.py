from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import UUID, Base, CIText, TZDateTime, created_at_col, uuid_fk, uuid_pk

EMAIL_PURPOSES = ("signup", "login")


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('signup', 'login')", name="ck_email_verifications_purpose"
        ),
        Index(
            "ix_email_verifications_lookup",
            "email",
            "purpose",
            text("created_at DESC"),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(CIText(), nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    attempts: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    created_at: Mapped[datetime] = created_at_col()


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_revoked", "user_id", "revoked_at"),)

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=text("now()"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )


class RateLimit(Base):
    __tablename__ = "rate_limits"
    __table_args__ = (Index("ix_rate_limits_updated_at", "updated_at"),)

    key: Mapped[str] = mapped_column(String, primary_key=True)
    count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    window_started_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=text("now()"), nullable=False
    )


__all__ = ["EmailVerification", "RefreshToken", "RateLimit"]
