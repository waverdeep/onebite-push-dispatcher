from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import UUID, Base, CIText, created_at_col, uuid_fk, uuid_pk

COMPANY_KINDS = ("company", "school", "gov", "org")
COMPANY_STATUSES = ("pending", "verified")


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('company', 'school', 'gov', 'org')",
            name="ck_companies_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'verified')",
            name="ck_companies_status",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(
        String, server_default=text("'company'"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, server_default=text("'pending'"), nullable=False
    )
    auto_created: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    member_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()


class CompanyDomain(Base):
    __tablename__ = "company_domains"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = uuid_fk("companies.id", ondelete="CASCADE")
    domain: Mapped[str] = mapped_column(CIText(), unique=True, nullable=False)


__all__ = ["Company", "CompanyDomain", "COMPANY_KINDS", "COMPANY_STATUSES"]
