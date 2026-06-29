from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import UUID, Base, TZDateTime, created_at_col, uuid_fk, uuid_pk

# Enum-like states as python constant tuples + CHECK constraints (project
# convention; DB enum types are avoided). See question.py / daily_quiz.py.
PACK_STATUSES = ("draft", "published", "archived")
PACK_PURCHASE_STATUSES = ("active", "completed", "cancelled")
# Transitional alias (renamed from PACK_SUB_STATUSES).
PACK_SUB_STATUSES = PACK_PURCHASE_STATUSES
PACK_ATTEMPT_STATUSES = ("in_progress", "completed", "abandoned")
PACK_UNLOCK_KINDS = ("scheduled", "advanced")


class Pack(Base):
    """A curated bundle of questions inside a category, delivered round by round.

    `subject_id` is denormalized (reachable via category) to keep "all packs in a
    subject" a single-index lookup. `question_count` / `total_rounds` are
    denormalized counters owned solely by the seed script (§6.8-3)."""

    __tablename__ = "packs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_packs_status",
        ),
        Index(
            "ix_packs_subject_category_status",
            "subject_id",
            "category_id",
            "status",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subjects.id"), nullable=False
    )
    category_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("categories.id"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    question_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    daily_count: Mapped[int] = mapped_column(
        SmallInteger, server_default=text("1"), nullable=False
    )
    total_rounds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String, server_default=text("'draft'"), nullable=False
    )
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at_col()
    published_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class PackQuestion(Base):
    """Many-to-many join (D2) with a curated, fixed order (D5). A question may
    belong to several packs. Round N = order_index slice."""

    __tablename__ = "pack_questions"
    __table_args__ = (
        PrimaryKeyConstraint("pack_id", "question_id"),
        UniqueConstraint(
            "pack_id", "order_index", name="uq_pack_questions_pack_order"
        ),
        Index("ix_pack_questions_question", "question_id"),
    )

    pack_id: Mapped[UUID] = uuid_fk("packs.id", ondelete="CASCADE")
    question_id: Mapped[UUID] = uuid_fk("questions.id")
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class PackPurchase(Base):
    """A user buying a pack + their round-based progress (§6.3). Round counter
    (rounds_unlocked) is the source of truth, not calendar dates.

    Renamed from PackSubscription (table pack_subscriptions -> pack_purchases) to
    mirror onebite-server. NOTE: this cron repo never queries pack purchases —
    the model is kept only to mirror the shared schema. `subscribed_at` and the
    `pack_subscriptions` VIEW survive on the server until its Contract phase;
    `purchased_at` is the going-forward column."""

    __tablename__ = "pack_purchases"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "pack_id", name="uq_pack_purchases_user_pack"
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_pack_purchases_status",
        ),
        Index("ix_pack_purchases_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    pack_id: Mapped[UUID] = uuid_fk("packs.id")
    status: Mapped[str] = mapped_column(
        String, server_default=text("'active'"), nullable=False
    )
    total_rounds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rounds_unlocked: Mapped[int] = mapped_column(
        SmallInteger, server_default=text("0"), nullable=False
    )
    last_round_on: Mapped[date | None] = mapped_column(Date)
    subscribed_at: Mapped[datetime] = created_at_col()
    purchased_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(TZDateTime)


# Transitional alias for the old class name.
PackSubscription = PackPurchase


class PackAttempt(Base):
    """One round's solve. No total_score column — packs never feed ranking
    (D6 / §5). Only correct_count is recorded."""

    __tablename__ = "pack_attempts"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "round_index", name="uq_pack_attempts_sub_round"
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_pack_attempts_status",
        ),
        CheckConstraint(
            "unlock_kind IN ('scheduled', 'advanced')",
            name="ck_pack_attempts_unlock_kind",
        ),
        Index("ix_pack_attempts_sub_round", "subscription_id", "round_index"),
        Index("ix_pack_attempts_purchase_round", "purchase_id", "round_index"),
    )

    id: Mapped[UUID] = uuid_pk()
    subscription_id: Mapped[UUID] = uuid_fk(
        "pack_purchases.id", ondelete="CASCADE"
    )
    purchase_id: Mapped[UUID | None] = uuid_fk(
        "pack_purchases.id", ondelete="CASCADE", nullable=True
    )
    pack_id: Mapped[UUID] = uuid_fk("packs.id")
    round_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    unlock_kind: Mapped[str] = mapped_column(
        String, server_default=text("'scheduled'"), nullable=False
    )
    opened_at: Mapped[datetime] = created_at_col()
    status: Mapped[str] = mapped_column(
        String, server_default=text("'in_progress'"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    abandoned_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    correct_count: Mapped[int | None] = mapped_column(SmallInteger)


class PackAttemptAnswer(Base):
    """One answer in a pack round. No score columns — speed bonus / scoring is a
    daily-only concept (§5)."""

    __tablename__ = "pack_attempt_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "question_id", name="uq_paa_attempt_question"
        ),
        # 4 = multiple_select (sorted comma-joined choice ids in answer_text);
        # 5 is reserved for a future ordering type (same answer_text shape).
        CheckConstraint("answer_type IN (1, 2, 3, 4, 5)", name="ck_paa_answer_type"),
        CheckConstraint(
            "gave_up OR ("
            "(answer_type = 1 AND selected_choice_id IS NOT NULL AND answer_text IS NULL)"
            " OR (answer_type IN (2, 3, 4, 5) AND selected_choice_id IS NULL"
            " AND answer_text IS NOT NULL))",
            name="ck_paa_answer_shape",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    attempt_id: Mapped[UUID] = uuid_fk("pack_attempts.id", ondelete="CASCADE")
    question_id: Mapped[UUID] = uuid_fk("questions.id")
    answer_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    selected_choice_id: Mapped[UUID | None] = uuid_fk(
        "question_choices.id", nullable=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime] = created_at_col()
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    # "모르겠어요" — see DailyAttemptAnswer.gave_up.
    gave_up: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    elapsed_ms: Mapped[int | None] = mapped_column(Integer)


__all__ = [
    "Pack",
    "PackQuestion",
    "PackPurchase",
    "PackSubscription",  # transitional alias
    "PackAttempt",
    "PackAttemptAnswer",
    "PACK_STATUSES",
    "PACK_PURCHASE_STATUSES",
    "PACK_SUB_STATUSES",  # transitional alias
    "PACK_ATTEMPT_STATUSES",
    "PACK_UNLOCK_KINDS",
]
