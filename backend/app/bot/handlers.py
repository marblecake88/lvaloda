"""Telegram bot: /start, /remind, voice-message fallback chat."""

import io
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db.models import ChatSession
from app.db.models import Message as DBMessage
from app.db.models import User
from app.db.session import SessionLocal
from app.llm.audio import synthesize, transcribe
from app.llm.chat import dialog_reply
from app.llm.scenarios import get_scenario

log = logging.getLogger(__name__)
settings = get_settings()
router = Router()


def _webapp_kb(text: str = "Parunāties 💬") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=settings.webapp_url))]
        ]
    )


async def _get_or_create_user(tg_user) -> User:
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = result.scalar_one_or_none()
        if user is not None:
            return user
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
            return user
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
            return result.scalar_one()


@router.message(CommandStart())
async def on_start(msg: Message):
    await _get_or_create_user(msg.from_user)
    await msg.answer(
        "Sveiki! Es esmu tavs latviešu valodas sarunu partneris. "
        "Nāc, parunāsim par ikdienas tēmām vai pārbaudīsim sevi eksāmena režīmā.\n\n"
        "Привет! Жми кнопку, чтобы открыть мини-приложение. "
        "Можешь писать мне сюда голосовые — я отвечу голосом.",
        reply_markup=_webapp_kb(),
    )


@router.message(Command("remind"))
async def on_remind(msg: Message, command: CommandObject):
    arg = (command.args or "").strip()
    if not arg:
        await msg.answer(
            "Укажи время в формате HH:MM (Rīgas laiks). Например: /remind 19:00"
        )
        return

    try:
        hh, mm = map(int, arg.split(":"))
        assert 0 <= hh <= 23 and 0 <= mm <= 59
    except (ValueError, AssertionError):
        await msg.answer("Неверный формат. Пример: /remind 19:00")
        return

    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == msg.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await msg.answer("Сначала напиши /start")
            return
        user.reminder_time = f"{hh:02d}:{mm:02d}"
        await db.commit()

    from app.bot.scheduler import reschedule_user

    await reschedule_user(msg.from_user.id, f"{hh:02d}:{mm:02d}")

    await msg.answer(
        f"Ежедневное напоминание поставлено на {hh:02d}:{mm:02d} ({settings.timezone})."
    )


@router.message(Command("remind_off"))
async def on_remind_off(msg: Message):
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == msg.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await msg.answer("Нет профиля. /start")
            return
        user.reminder_time = None
        await db.commit()

    from app.bot.scheduler import cancel_user

    cancel_user(msg.from_user.id)
    await msg.answer("Напоминания выключены.")


@router.message(F.voice)
async def on_voice(msg: Message, bot: Bot):
    """Fallback voice chat through the bot (free-chat scenario)."""
    user = await _get_or_create_user(msg.from_user)

    # Download voice file
    file = await bot.get_file(msg.voice.file_id)
    buf = io.BytesIO()
    await bot.download_file(file.file_path, buf)
    buf.seek(0)
    audio_bytes = buf.read()

    try:
        user_text = await transcribe(audio_bytes, filename="voice.ogg")
    except Exception as e:
        log.exception("STT failed")
        await msg.answer(f"Не смог распознать голос: {e}")
        return

    await msg.answer(f"🎙️ «{user_text}»")

    scenario = get_scenario("brivais_cats")
    if not scenario:
        await msg.answer("Ошибка конфига сценариев")
        return

    async with SessionLocal() as db:
        # Find or create an ongoing bot-voice free-chat session
        result = await db.execute(
            select(ChatSession)
            .where(
                ChatSession.user_id == user.id,
                ChatSession.scenario == "brivais_cats",
                ChatSession.mode == "dialog",
                ChatSession.finished_at.is_(None),
            )
            .order_by(ChatSession.id.desc())
        )
        session = result.scalars().first()
        if session is None:
            session = ChatSession(user_id=user.id, mode="dialog", scenario="brivais_cats")
            db.add(session)
            await db.commit()
            await db.refresh(session)

        db.add(DBMessage(session_id=session.id, role="user", content=user_text))
        await db.commit()

        result = await db.execute(
            select(DBMessage)
            .where(DBMessage.session_id == session.id)
            .order_by(DBMessage.id)
        )
        history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    reply = await dialog_reply(scenario, history)

    async with SessionLocal() as db:
        db.add(DBMessage(session_id=session.id, role="assistant", content=reply))
        await db.commit()

    # Send text + voice
    await msg.answer(reply)
    try:
        audio_out = await synthesize(reply)
        await msg.answer_voice(
            BufferedInputFile(audio_out, filename="reply.mp3"),
        )
    except Exception:
        log.exception("TTS failed")
