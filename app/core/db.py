from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import String, UserDefinedType

from app.core.config import settings


class CIText(UserDefinedType):
    """Postgres citext type (case-insensitive text). Avoids pulling in
    psycopg2 the way sqlalchemy-citext does; works with asyncpg as plain text."""

    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "CITEXT"

    def bind_processor(self, dialect):  # noqa: ANN001
        return None

    def result_processor(self, dialect, coltype):  # noqa: ANN001
        return None

    def python_type(self) -> type:
        return str

    class comparator_factory(String.Comparator):  # noqa: N801
        pass


def _connect_args() -> dict:
    """asyncpg connect args tuned for Supabase PgBouncer transaction pooler.

    - statement_cache_size=0: transaction pooling does not support prepared
      statements, so the asyncpg cache must be disabled.
    - server_settings.search_path: every connection defaults to the onebite schema.
    """
    args: dict = {
        "statement_cache_size": 0,
        "server_settings": {"search_path": settings.DB_SCHEMA},
    }
    if settings.DB_SSL:
        args["ssl"] = "require"
    return args


engine = create_async_engine(
    settings.async_dsn,
    pool_pre_ping=True,
    connect_args=_connect_args(),
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(AsyncAttrs, DeclarativeBase):
    """All tables live in the onebite schema."""

    metadata = MetaData(schema=settings.DB_SCHEMA)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# --- reusable column factories (keep the 25 models consistent & concise) ---
from sqlalchemy import ForeignKey, text  # noqa: E402
from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # noqa: E402
from sqlalchemy.orm import mapped_column as _mc  # noqa: E402

TZDateTime = DateTime(timezone=True)


def uuid_pk():
    return _mc(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def uuid_fk(target: str, *, nullable: bool = False, ondelete: str | None = None):
    return _mc(
        PG_UUID(as_uuid=True),
        ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
    )


def created_at_col():
    return _mc(TZDateTime, server_default=func.now(), nullable=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "Base",
    "TimestampMixin",
    "TZDateTime",
    "CIText",
    "PG_UUID",
    "uuid_pk",
    "uuid_fk",
    "created_at_col",
    "engine",
    "SessionLocal",
    "get_db",
    "UUID",
]
