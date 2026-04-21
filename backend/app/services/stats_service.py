"""Daily practice stats: streak, minutes, topic coverage.

`record_message` is cheap to call from every message path and handles the
unique `(user_id, stat_date)` upsert idiomatically for SQLite.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DailyStats, User

log = logging.getLogger(__name__)

# Very rough heuristic: treat each inbound message as ~20 seconds of engagement.
_SECONDS_PER_MESSAGE = 20

# Practice goal default — can later be made per-user.
DAILY_GOAL_MINUTES = 15


def _today() -> date:
    return datetime.utcnow().date()


async def _upsert_today(db: AsyncSession, user_id: int, topic: str | None) -> DailyStats:
    today = _today()
    row = (
        await db.execute(
            select(DailyStats).where(
                DailyStats.user_id == user_id, DailyStats.stat_date == today
            )
        )
    ).scalar_one_or_none()

    if row is None:
        row = DailyStats(
            user_id=user_id,
            stat_date=today,
            messages_sent=0,
            seconds_spent=0,
            topics=[],
        )
        db.add(row)
        try:
            await db.flush()
        except IntegrityError:
            # Concurrent insert — re-fetch.
            await db.rollback()
            row = (
                await db.execute(
                    select(DailyStats).where(
                        DailyStats.user_id == user_id,
                        DailyStats.stat_date == today,
                    )
                )
            ).scalar_one()

    row.messages_sent = (row.messages_sent or 0) + 1
    row.seconds_spent = (row.seconds_spent or 0) + _SECONDS_PER_MESSAGE
    if topic and topic not in (row.topics or []):
        row.topics = [*(row.topics or []), topic]
    return row


async def record_message(
    db: AsyncSession, user_id: int, topic: str | None
) -> None:
    try:
        await _upsert_today(db, user_id, topic)
        await db.commit()
    except Exception:
        log.exception("record_message failed")
        await db.rollback()


async def compute_streak(db: AsyncSession, user_id: int) -> int:
    """Consecutive days with messages_sent > 0 ending today-or-yesterday."""
    result = await db.execute(
        select(DailyStats.stat_date)
        .where(DailyStats.user_id == user_id, DailyStats.messages_sent > 0)
        .order_by(DailyStats.stat_date.desc())
    )
    dates = [r[0] for r in result.all()]
    if not dates:
        return 0
    today = _today()
    # Allow "today or yesterday" as the anchor so a user who hasn't practiced
    # yet today still sees their streak.
    anchor = dates[0]
    if anchor != today and anchor != today - timedelta(days=1):
        return 0
    streak = 1
    prev = anchor
    for d in dates[1:]:
        if prev - d == timedelta(days=1):
            streak += 1
            prev = d
        else:
            break
    return streak


async def summary(db: AsyncSession, user_id: int) -> dict:
    today = _today()
    week_ago = today - timedelta(days=6)

    today_row = (
        await db.execute(
            select(DailyStats).where(
                DailyStats.user_id == user_id, DailyStats.stat_date == today
            )
        )
    ).scalar_one_or_none()

    week = (
        await db.execute(
            select(DailyStats)
            .where(
                DailyStats.user_id == user_id,
                DailyStats.stat_date >= week_ago,
            )
            .order_by(DailyStats.stat_date)
        )
    ).scalars().all()

    # last 30 days for calendar
    month_ago = today - timedelta(days=29)
    month_rows = (
        await db.execute(
            select(DailyStats)
            .where(
                DailyStats.user_id == user_id,
                DailyStats.stat_date >= month_ago,
            )
        )
    ).scalars().all()
    calendar = {
        row.stat_date.isoformat(): {
            "messages": row.messages_sent or 0,
            "minutes": round((row.seconds_spent or 0) / 60, 1),
        }
        for row in month_rows
    }

    streak = await compute_streak(db, user_id)

    # Topic coverage: dict[topic_key] = days_practiced_last_30
    topic_counts: dict[str, int] = {}
    for row in month_rows:
        for t in row.topics or []:
            topic_counts[t] = topic_counts.get(t, 0) + 1

    return {
        "streak": streak,
        "goal_minutes": DAILY_GOAL_MINUTES,
        "today_minutes": round(((today_row.seconds_spent if today_row else 0) or 0) / 60, 1),
        "today_messages": today_row.messages_sent if today_row else 0,
        "week_minutes": round(sum((r.seconds_spent or 0) for r in week) / 60, 1),
        "week_days_active": sum(1 for r in week if (r.messages_sent or 0) > 0),
        "calendar": calendar,
        "topic_counts": topic_counts,
    }


async def weekly_report(db: AsyncSession, user_id: int) -> dict:
    """Richer report for the bot's Monday summary."""
    s = await summary(db, user_id)
    today = _today()
    week_ago = today - timedelta(days=6)

    week = (
        await db.execute(
            select(DailyStats)
            .where(
                DailyStats.user_id == user_id,
                DailyStats.stat_date >= week_ago,
            )
        )
    ).scalars().all()

    top_topics = sorted(
        ({t for r in week for t in (r.topics or [])}),
        key=lambda t: sum(
            1 for r in week if t in (r.topics or [])
        ),
        reverse=True,
    )[:3]

    return {
        **s,
        "top_topics": top_topics,
    }


async def get_user(db: AsyncSession, telegram_id: int) -> User | None:
    return (
        await db.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()


# Suppress "unused import" warnings in some editors
_ = func
