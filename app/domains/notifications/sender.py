"""Shared Web Push delivery (ADR 0002).

A notification event has two representations: a durable in-app row (always
written, so the notification center stays complete even for users with no push
subscription) and a best-effort push to each of the user's device
subscriptions. `deliver()` does both.

IMPORTANT — drift boundary: this module imports ONLY app.models, app.core.config
and pywebpush. It must NOT import fastapi / app.core.deps / any web layer, so the
onebite-push-dispatcher Job can copy it verbatim (same rule as the publisher).
The caller owns the commit (get_db autocommits on request paths; the dispatcher
commits explicitly).
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Notification, PushSubscription

logger = logging.getLogger("onebite")

# Endpoints that 404/410 are permanently gone (unsubscribed / expired) and are
# pruned. Other failures are transient and only logged.
_GONE_STATUSES = (404, 410)


def _push_one(sub: PushSubscription, payload: str) -> None:
    """Blocking single send (pywebpush is sync). Run via asyncio.to_thread.
    Raises WebPushException on HTTP failure."""
    webpush(
        subscription_info={
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        },
        data=payload,
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": settings.VAPID_SUBJECT},
    )


async def deliver(
    db: AsyncSession,
    user_id: UUID,
    *,
    type: str,
    title: str,
    body: str,
    link: str | None = None,
) -> Notification:
    """Persist an in-app notification and push it to all the user's devices.

    Always writes the Notification row (even with zero subscriptions). Sends to
    each subscription; prunes endpoints that report 404/410. Returns the created
    Notification. Does NOT commit."""
    notification = Notification(
        user_id=user_id, type=type, title=title, body=body, link=link
    )
    db.add(notification)
    await db.flush()

    subs = (
        await db.scalars(
            select(PushSubscription).where(
                PushSubscription.user_id == user_id
            )
        )
    ).all()
    if not subs:
        return notification

    payload = json.dumps(
        {"type": type, "title": title, "body": body, "link": link}
    )
    gone_ids: list[UUID] = []
    now = datetime.now(UTC)
    for sub in subs:
        try:
            await asyncio.to_thread(_push_one, sub, payload)
            sub.last_used_at = now
        except WebPushException as exc:
            status_code = getattr(
                getattr(exc, "response", None), "status_code", None
            )
            if status_code in _GONE_STATUSES:
                gone_ids.append(sub.id)
            else:
                logger.warning(
                    "web push failed (status=%s) for subscription %s",
                    status_code,
                    sub.id,
                )
        except Exception:
            logger.exception(
                "unexpected web push error for subscription %s", sub.id
            )

    if gone_ids:
        await db.execute(
            delete(PushSubscription).where(PushSubscription.id.in_(gone_ids))
        )

    await db.flush()
    return notification
