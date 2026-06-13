"""run_last_call selection-logic tests (real Supabase, sender.deliver mocked).

The deadline-near nudge must go to exactly: push-enabled users with a streak to
lose (current_streak > 0) who have NOT completed today's quiz for their daily
domain, and only once per day. These tests pin that selection by seeding a few
users on an isolated throwaway domain (so nothing collides with production data)
and asserting which user_ids run_last_call hands to sender.deliver.

sender.deliver is monkeypatched to just record user_ids — no VAPID / Web Push.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from sqlalchemy import delete, text

import job_main
from app.domains.notifications import sender
from app.domains.notifications.adaptive import KST
from app.models import (
    DailyAttempt,
    DailyQuiz,
    Domain,
    Notification,
    User,
    UserSettings,
    UserStats,
)


def _kst_today():
    return datetime.now(KST).date()


def _day_start_utc() -> datetime:
    now_kst = datetime.now(KST)
    midnight = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(UTC)


def _mk_user(email_tag: str) -> User:
    suffix = uuid.uuid4().hex[:10]
    return User(email=f"lc_{email_tag}_{suffix}@example.com", nickname=f"lc_{suffix}")


@pytest_asyncio.fixture
async def seeded(db_sessionmaker):
    """Seed an isolated domain + today's quiz + a matrix of users, yield their
    ids, then tear everything down. Returns a dict of labelled user ids + the
    domain id so the test can assert against specific rows."""
    domain_id = f"test-lc-{uuid.uuid4().hex[:8]}"
    track_id = f"{domain_id}-all"
    today = _kst_today()
    created_user_ids: list[uuid.UUID] = []
    quiz_id = None
    try:
        async with db_sessionmaker() as db:
            db.add(
                Domain(id=domain_id, name="LastCall Test", display_order=9999)
            )
            await db.flush()
            # Track + DailyQuiz via raw SQL: the real daily_quizzes table requires
            # a NOT NULL track_id (FK → tracks), but this dispatcher's drifted
            # DailyQuiz model omits the column. Insert explicitly to satisfy it.
            await db.execute(
                text(
                    "INSERT INTO tracks (id, domain_id, name, display_order) "
                    "VALUES (:id, :domain_id, :name, 9999)"
                ),
                {"id": track_id, "domain_id": domain_id, "name": "LastCall Track"},
            )
            quiz_id = uuid.uuid4()
            await db.execute(
                text(
                    "INSERT INTO daily_quizzes "
                    "(id, domain_id, track_id, quiz_date, opens_at, closes_at) "
                    "VALUES (:id, :domain_id, :track_id, :qd, :opens, :closes)"
                ),
                {
                    "id": quiz_id,
                    "domain_id": domain_id,
                    "track_id": track_id,
                    "qd": today,
                    "opens": datetime.now(UTC) - timedelta(days=1),
                    "closes": datetime.now(UTC) + timedelta(hours=2),
                },
            )
            await db.flush()

            labels = {
                # at-risk, push on, not completed → SHOULD be nudged
                "target": dict(streak=5, push=True, completed=False),
                # streak 0 → excluded (nothing to lose) — the fix under test
                "no_streak": dict(streak=0, push=True, completed=False),
                # completed today → excluded
                "completed": dict(streak=5, push=True, completed=True),
                # push off → excluded
                "push_off": dict(streak=5, push=False, completed=False),
            }
            ids: dict[str, uuid.UUID] = {}
            for label, cfg in labels.items():
                user = _mk_user(label)
                db.add(user)
                await db.flush()
                ids[label] = user.id
                created_user_ids.append(user.id)
                db.add(
                    UserSettings(
                        user_id=user.id,
                        daily_push_enabled=cfg["push"],
                        daily_domain_id=domain_id,
                    )
                )
                db.add(
                    UserStats(user_id=user.id, current_streak=cfg["streak"])
                )
                if cfg["completed"]:
                    db.add(
                        DailyAttempt(
                            user_id=user.id,
                            daily_quiz_id=quiz_id,
                            status="completed",
                            completed_at=datetime.now(UTC),
                        )
                    )
            await db.commit()

        yield {"ids": ids, "domain_id": domain_id, "quiz_id": quiz_id}
    finally:
        async with db_sessionmaker() as db:
            if quiz_id is not None:
                await db.execute(
                    delete(DailyAttempt).where(
                        DailyAttempt.daily_quiz_id == quiz_id
                    )
                )
            for uid in created_user_ids:
                await db.execute(
                    delete(Notification).where(Notification.user_id == uid)
                )
                await db.execute(
                    delete(UserStats).where(UserStats.user_id == uid)
                )
                await db.execute(
                    delete(UserSettings).where(UserSettings.user_id == uid)
                )
            if quiz_id is not None:
                await db.execute(delete(DailyQuiz).where(DailyQuiz.id == quiz_id))
            await db.execute(
                text("DELETE FROM tracks WHERE id = :id"), {"id": track_id}
            )
            for uid in created_user_ids:
                await db.execute(delete(User).where(User.id == uid))
            await db.execute(delete(Domain).where(Domain.id == domain_id))
            await db.commit()


async def _run_collecting(db_sessionmaker, monkeypatch) -> set:
    """Run run_last_call with sender.deliver mocked; return the set of user_ids
    it tried to deliver to (restricted to our seeded users by the caller)."""
    delivered: list = []

    async def fake_deliver(db, user_id, **kwargs):
        delivered.append(user_id)
        # still write the Notification row so the idempotency guard is exercised
        n = Notification(
            user_id=user_id,
            type=kwargs["type"],
            title=kwargs["title"],
            body=kwargs["body"],
            link=kwargs.get("link"),
        )
        db.add(n)
        await db.flush()
        return n

    monkeypatch.setattr(sender, "deliver", fake_deliver)

    async with db_sessionmaker() as db:
        await job_main.run_last_call(db, _day_start_utc())
        await db.commit()
    return set(delivered)


async def test_last_call_only_at_risk_uncompleted(
    db_sessionmaker, monkeypatch, seeded
):
    ids = seeded["ids"]
    delivered = await _run_collecting(db_sessionmaker, monkeypatch)

    assert ids["target"] in delivered  # at-risk, uncompleted → nudged
    assert ids["no_streak"] not in delivered  # streak 0 → excluded (the fix)
    assert ids["completed"] not in delivered  # done today → excluded
    assert ids["push_off"] not in delivered  # push off → excluded


async def test_last_call_idempotent_same_day(
    db_sessionmaker, monkeypatch, seeded
):
    ids = seeded["ids"]
    first = await _run_collecting(db_sessionmaker, monkeypatch)
    assert ids["target"] in first

    # Second run the same day: the target already has a daily_last_call
    # Notification (written by the mocked deliver), so it must be skipped.
    second = await _run_collecting(db_sessionmaker, monkeypatch)
    assert ids["target"] not in second
