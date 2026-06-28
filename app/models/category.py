from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, created_at_col


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_active_order", "is_active", "display_order"),
        Index("ix_categories_subject_order", "subject_id", "display_order"),
    )

    # slug-style varchar PK (e.g. "algorithm", "os"); doubles as the public/URL
    # identifier, so no separate slug column.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_id: Mapped[str] = mapped_column(
        String, ForeignKey("subjects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    icon: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at_col()


__all__ = ["Category"]
