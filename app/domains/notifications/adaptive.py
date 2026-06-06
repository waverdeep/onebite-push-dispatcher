"""Adaptive daily-reminder hour (ADR 0002 결정 F).

The reminder hour learns from when the user actually solves: the median of their
recent solve times, rounded to the nearest whole hour. Median (not the last
value) keeps a one-off late-night solve from yanking the schedule around. No data
in the window → return None (keep the current value). 13 is the cold-start
default (set as the column server_default in PR1).

IMPORTANT — drift boundary: imports ONLY app.models / stdlib (NO fastapi / web
layer), so onebite-push-dispatcher copies it verbatim. The caller commits.
"""

import statistics
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyAttempt

KST = ZoneInfo("Asia/Seoul")
LEARN_WINDOW_DAYS = 7


def compute_push_hour(completed_times_kst: list[datetime]) -> int | None:
    """Pure: median of solve times (as fractional hours, e.g. 13:42 → 13.7),
    rounded to the nearest whole hour in [0, 23]. Empty → None."""
    if not completed_times_kst:
        return None
    fractional = [t.hour + t.minute / 60 for t in completed_times_kst]
    median = statistics.median(fractional)
    # Round to nearest hour; 23.5 rounds to 24 → wrap to 0.
    return round(median) % 24


async def learn_push_hour(db: AsyncSession, user_id: UUID) -> int | None:
    """Look at the user's completed daily attempts in the last 7 days (KST) and
    return the learned reminder hour, or None if there's no data (keep current).
    Caller decides whether to write it (and only when daily_push_hour_auto)."""
    cutoff = datetime.now(UTC) - timedelta(days=LEARN_WINDOW_DAYS)
    rows = (
        await db.scalars(
            select(DailyAttempt.completed_at).where(
                DailyAttempt.user_id == user_id,
                DailyAttempt.status == "completed",
                DailyAttempt.completed_at.is_not(None),
                DailyAttempt.completed_at >= cutoff,
            )
        )
    ).all()
    # completed_at is stored tz-aware (UTC); convert to KST before extracting hour.
    times_kst = [ts.astimezone(KST) for ts in rows if ts is not None]
    return compute_push_hour(times_kst)
