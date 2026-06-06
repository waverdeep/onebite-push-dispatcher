"""Cloud Run Job entrypoint for the adaptive daily-reminder dispatcher (ADR 0002).

This is the container's `CMD`. Cloud Run Jobs run it to completion: a clean exit
(0) marks the execution successful, a non-zero exit fails it and lets the
scheduler retry.

Cloud Scheduler triggers this once an hour (`0 * * * *`, Asia/Seoul). Each run:
  1. Resolve the current KST hour (the send slot).
  2. Find users whose reminder is due this slot (daily_push_enabled AND
     daily_push_hour == slot AND not deleted).
  3. For each — unless a daily_reminder was already sent today (idempotency) —
     deliver() a push + persist the in-app notification.
  4. Re-learn that user's reminder hour from recent solves and store it for
     tomorrow (only when daily_push_hour_auto).

Override the slot for local testing with PUSH_HOUR=14 or the first CLI arg.

sender.deliver / adaptive.learn_push_hour are copied verbatim from onebite-server
(they import no web layer). Keep this project's app/ in sync when the server's
models / sender / adaptive change (same drift rule as the publisher).
"""

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime

from sqlalchemy import and_, exists, select

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.domains.notifications import adaptive, sender
from app.domains.notifications.adaptive import KST
from app.models import Notification, User, UserSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("push_dispatcher_job")

REMINDER_TYPE = "daily_reminder"
REMINDER_TITLE = "오늘의 한입"
REMINDER_BODY = "오늘의 퀴즈가 기다리고 있어요 🍙"
REMINDER_LINK = "/"


def resolve_slot_hour() -> int:
    raw = sys.argv[1] if len(sys.argv) > 1 else os.getenv("PUSH_HOUR")
    if raw:
        return int(raw.strip())
    return datetime.now(KST).hour


def _kst_day_start_utc() -> datetime:
    """UTC instant of 00:00 KST today — the idempotency window boundary."""
    now_kst = datetime.now(KST)
    midnight_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_kst.astimezone(UTC)


async def run(slot_hour: int) -> None:
    log.info(
        "dispatching daily reminders for KST hour=%d (env=%s)",
        slot_hour,
        settings.ENV,
    )
    sent = 0
    day_start = _kst_day_start_utc()
    try:
        async with SessionLocal() as db:
            # A reminder already written for this user today (idempotency guard
            # against duplicate/retried scheduler triggers).
            already_today = (
                select(Notification.id)
                .where(
                    Notification.user_id == User.id,
                    Notification.type == REMINDER_TYPE,
                    Notification.created_at >= day_start,
                )
                .correlate(User)
            )
            rows = (
                await db.execute(
                    select(User.id, UserSettings.daily_push_hour_auto)
                    .join(UserSettings, UserSettings.user_id == User.id)
                    .where(
                        and_(
                            UserSettings.daily_push_enabled.is_(True),
                            UserSettings.daily_push_hour == slot_hour,
                            User.deleted_at.is_(None),
                            ~exists(already_today),
                        )
                    )
                )
            ).all()

            for user_id, auto in rows:
                await sender.deliver(
                    db,
                    user_id,
                    type=REMINDER_TYPE,
                    title=REMINDER_TITLE,
                    body=REMINDER_BODY,
                    link=REMINDER_LINK,
                )
                sent += 1

                # Re-learn the reminder hour for tomorrow (auto users only).
                if auto:
                    learned = await adaptive.learn_push_hour(db, user_id)
                    if learned is not None and learned != slot_hour:
                        settings_row = await db.get(UserSettings, user_id)
                        if settings_row is not None:
                            settings_row.daily_push_hour = learned

            await db.commit()
    finally:
        await engine.dispose()

    log.info("dispatch hour=%d done: sent=%d", slot_hour, sent)


def main() -> None:
    try:
        slot_hour = resolve_slot_hour()
    except ValueError as exc:
        log.error("invalid push hour: %s", exc)
        sys.exit(2)

    if not 0 <= slot_hour <= 23:
        log.error("push hour out of range: %d", slot_hour)
        sys.exit(2)

    try:
        asyncio.run(run(slot_hour))
    except Exception:
        log.exception("dispatch job failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
