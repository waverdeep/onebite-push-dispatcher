from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import UUID, Base, TZDateTime, created_at_col, uuid_fk, uuid_pk

QUESTION_TYPES = ("ox", "multiple_choice", "short_answer", "multiple_select")
QUESTION_STATUSES = ("draft", "reviewed", "published", "archived")
REPORT_REASONS = ("wrong_answer", "typo", "ambiguous", "other")
REPORT_STATUSES = ("open", "resolved", "dismissed")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('ox', 'multiple_choice', 'short_answer', 'multiple_select')",
            name="ck_questions_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'reviewed', 'published', 'archived')",
            name="ck_questions_status",
        ),
        Index("ix_questions_status_category", "status", "category_id"),
        Index("ix_questions_type", "type"),
        Index("ix_questions_last_used_at", "last_used_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    category_id: Mapped[str] = mapped_column(
        String, ForeignKey("categories.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String, server_default=text("'draft'"), nullable=False
    )
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by: Mapped[UUID | None] = uuid_fk("users.id", nullable=True)
    created_at: Mapped[datetime] = created_at_col()
    published_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    use_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )


class QuestionChoice(Base):
    __tablename__ = "question_choices"

    id: Mapped[UUID] = uuid_pk()
    question_id: Mapped[UUID] = uuid_fk("questions.id", ondelete="CASCADE")
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)


class QuestionAnswer(Base):
    __tablename__ = "question_answers"
    __table_args__ = (
        Index("ix_question_answers_normalized", "question_id", "normalized_value"),
    )

    id: Mapped[UUID] = uuid_pk()
    question_id: Mapped[UUID] = uuid_fk("questions.id", ondelete="CASCADE")
    value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )


class QuestionReport(Base):
    __tablename__ = "question_reports"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "reporter_id", name="uq_question_reports_reporter"
        ),
        CheckConstraint(
            "reason IN ('wrong_answer', 'typo', 'ambiguous', 'other')",
            name="ck_question_reports_reason",
        ),
        CheckConstraint(
            "status IN ('open', 'resolved', 'dismissed')",
            name="ck_question_reports_status",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    question_id: Mapped[UUID] = uuid_fk("questions.id", ondelete="CASCADE")
    reporter_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    reason: Mapped[str] = mapped_column(String, nullable=False)
    memo: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String, server_default=text("'open'"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()


__all__ = ["Question", "QuestionChoice", "QuestionAnswer", "QuestionReport"]
