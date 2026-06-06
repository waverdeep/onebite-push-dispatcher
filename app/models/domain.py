from datetime import datetime

from sqlalchemy import Boolean, Index, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, created_at_col


class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (Index("ix_domains_active_order", "is_active", "display_order"),)

    # slug-style varchar PK (e.g. "cs"); doubles as the public/URL identifier,
    # so no separate slug column. Top-level grouping above Category.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()


__all__ = ["Domain"]
