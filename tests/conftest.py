"""Test fixtures for the push dispatcher.

Hits the real Supabase DB like onebite-server's suite (the dispatcher has no
schema of its own — it reads the shared tables). We route through the *session*
pooler (5432) instead of the transaction pooler (6543) so prepared statements
work and connection setup is cheap (mirrors onebite-server/tests/conftest.py).

These tests validate query/selection logic only — sender.deliver is monkeypatched
in each test, so no VAPID keys or real Web Push are needed.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db import _connect_args


def _test_connect_args() -> dict:
    """Session-pooler connect args: re-enable prepared statements (the session
    pooler gives each connection a dedicated backend, unlike the transaction
    pooler which forces statement_cache_size=0)."""
    args = _connect_args()
    args.pop("statement_cache_size", None)
    return args


@pytest_asyncio.fixture
async def db_sessionmaker():
    """Fresh NullPool engine on the session pooler (5432), bound to this test's
    event loop (the module-global pooled engine caches across loops, which
    breaks under pytest-asyncio's per-test loops)."""
    dsn = settings.async_dsn.replace(":6543", ":5432")
    engine = create_async_engine(
        dsn, poolclass=NullPool, connect_args=_test_connect_args()
    )
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield maker
    finally:
        await engine.dispose()
