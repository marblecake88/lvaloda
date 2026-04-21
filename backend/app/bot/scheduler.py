"""Daily reminders via APScheduler."""

import logging
import random

import pytz
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import get_settings
from app.db.models import User
from app.db.session import SessionLocal
from app.llm.client import grok
from app.llm.scenarios import DAILY_SITUATIONS, EXAM_TOPICS
from app.services import stats_service

log = logging.getLogger(__name__)
settings = get_settings()

_scheduler: AsyncIOScheduler | None = None
_bot: Bot | None = None


def init_scheduler(bot: Bot) -> AsyncIOScheduler:
    global _scheduler, _bot
    _bot = bot
    tz = pytz.timezone(settings.timezone)
    _scheduler = AsyncIOScheduler(timezone=tz)
    _scheduler.start()

    # Weekly summary — every Monday 10:00 Rīgas laiks for all users.
    _scheduler.add_job(
        _send_weekly_summaries,
        trigger=CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="weekly_summary",
        replace_existing=True,
    )

    log.info("Scheduler started (tz=%s)", settings.timezone)
    return _scheduler


async def _pick_topic(day_index: int):
    """Alternate: even day → exam topic, odd day → daily situation."""
    if day_index % 2 == 0:
        return random.choice(EXAM_TOPICS)
    return random.choice(DAILY_SITUATIONS)


async def _send_reminder(telegram_id: int):
    if _bot is None:
        return
    from datetime import date

    topic = await _pick_topic(date.today().toordinal())
    kind_emoji = "📝" if topic.kind == "exam" else "💬"

    text = (
        f"{kind_emoji} Sveiks! Šodienas tēma:\n\n"
        f"**{topic.title_lv}**\n"
        f"_{topic.title_ru}_\n\n"
        f"Nāc parunāties, jātrenē!"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Sākt 🚀",
                    web_app=WebAppInfo(
                        url=f"{settings.webapp_url}?scenario={topic.key}"
                    ),
                )
            ]
        ]
    )
    try:
        await _bot.send_message(telegram_id, text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        log.exception("Failed to send reminder to %s", telegram_id)


async def reschedule_user(telegram_id: int, hhmm: str):
    if _scheduler is None:
        return
    hh, mm = map(int, hhmm.split(":"))
    job_id = f"reminder:{telegram_id}"
    _scheduler.add_job(
        _send_reminder,
        trigger=CronTrigger(hour=hh, minute=mm),
        args=[telegram_id],
        id=job_id,
        replace_existing=True,
    )
    log.info("Scheduled reminder for %s at %s", telegram_id, hhmm)


def cancel_user(telegram_id: int):
    if _scheduler is None:
        return
    job_id = f"reminder:{telegram_id}"
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        pass


async def load_schedules_from_db():
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.reminder_time.is_not(None)))
        for user in result.scalars().all():
            if user.reminder_time:
                await reschedule_user(user.telegram_id, user.reminder_time)


_WEEKLY_PROMPT = """На основании статистики недельной практики латышского ученика \
сгенерируй короткое дружелюбное сообщение в Telegram (3-5 строк, по-русски). \
Данные:
- Стрик: {streak} дней
- Минут за неделю: {week_minutes}
- Активных дней: {week_days_active} / 7
- Топ темы: {top_topics}

Требования:
- Без формальщины, живой тон.
- Отметь что идёт хорошо (стрик, минуты) и аккуратно подскажи что подтянуть (если активных дней мало).
- Закончи мотивирующим призывом вернуться на этой неделе.
- БЕЗ markdown, БЕЗ эмодзи в избытке — максимум 1-2."""


async def _weekly_text_for(user_id: int) -> str | None:
    async with SessionLocal() as db:
        report = await stats_service.weekly_report(db, user_id)
    if report["week_days_active"] == 0:
        return (
            "Эй, на этой неделе мы не виделись :)\n"
            "Давай вернёмся — 10 минут живого разговора на латышском уже даст эффект."
        )
    prompt = _WEEKLY_PROMPT.format(
        streak=report["streak"],
        week_minutes=report["week_minutes"],
        week_days_active=report["week_days_active"],
        top_topics=", ".join(report.get("top_topics") or []) or "—",
    )
    try:
        resp = await grok.chat.completions.create(
            model=settings.xai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return resp.choices[0].message.content or None
    except Exception:
        log.exception("weekly text generation failed")
        return None


async def _send_weekly_summaries():
    if _bot is None:
        return
    async with SessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
    for user in users:
        text = await _weekly_text_for(user.id)
        if not text:
            continue
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Отрыть приложение",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )]
            ]
        )
        try:
            await _bot.send_message(user.telegram_id, text, reply_markup=kb)
        except Exception:
            log.exception("weekly: failed to message %s", user.telegram_id)
