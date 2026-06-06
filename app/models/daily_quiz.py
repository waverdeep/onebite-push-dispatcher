from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import UUID, Base, TZDateTime, uuid_fk, uuid_pk

ATTEMPT_STATUSES = ("in_progress", "completed", "abandoned")
ANSWER_TYPES = (1, 2, 3)  # 1=mc, 2=ox, 3=short


class DailyQuiz(Base):
    __tablename__ = "daily_quizzes"
    __table_args__ = (
        UniqueConstraint(
            "domain_id", "quiz_date", name="uq_daily_quizzes_domain_date"
        ),
        Index("ix_daily_quizzes_date", "quiz_date"),
    )

    id: Mapped[UUID] = uuid_pk()
    domain_id: Mapped[str] = mapped_column(
        String, ForeignKey("domains.id"), nullable=False
    )
    quiz_date: Mapped[date] = mapped_column(Date, nullable=False)
    opens_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    closes_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)


class DailyQuizQuestion(Base):
    __tablename__ = "daily_quiz_questions"

    daily_quiz_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("daily_quizzes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    question_id: Mapped[UUID] = uuid_fk("questions.id")


class DailyAttempt(Base):
    __tablename__ = "daily_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "daily_quiz_id", name="uq_daily_attempts_user_quiz"),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_daily_attempts_status",
        ),
        Index("ix_daily_attempts_status_completed", "status", "completed_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = uuid_fk("users.id", ondelete="CASCADE")
    daily_quiz_id: Mapped[UUID] = uuid_fk("daily_quizzes.id")
    status: Mapped[str] = mapped_column(
        String, server_default=text("'in_progress'"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=text("now()"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    abandoned_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    correct_count: Mapped[int | None] = mapped_column(SmallInteger)
    total_score: Mapped[int | None] = mapped_column(Integer)


class DailyAttemptAnswer(Base):
    __tablename__ = "daily_attempt_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "question_id", name="uq_daily_attempt_answers_question"
        ),
        CheckConstraint("answer_type IN (1, 2, 3)", name="ck_daa_answer_type"),
        CheckConstraint(
            "(answer_type = 1 AND selected_choice_id IS NOT NULL AND answer_text IS NULL)"
            " OR (answer_type IN (2, 3) AND selected_choice_id IS NULL"
            " AND answer_text IS NOT NULL)",
            name="ck_daa_answer_shape",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    attempt_id: Mapped[UUID] = uuid_fk("daily_attempts.id", ondelete="CASCADE")
    question_id: Mapped[UUID] = uuid_fk("questions.id")
    answer_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    selected_choice_id: Mapped[UUID | None] = uuid_fk(
        "question_choices.id", nullable=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=text("now()"), nullable=False
    )
    is_correct: Mapped[bool | None] = mapped_column()
    elapsed_ms: Mapped[int | None] = mapped_column(Integer)
    base_score: Mapped[int | None] = mapped_column(Integer)
    bonus_score: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer)


__all__ = ["DailyQuiz", "DailyQuizQuestion", "DailyAttempt", "DailyAttemptAnswer"]
