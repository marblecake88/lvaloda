"""FastAPI app + aiogram bot webhook + scheduler."""

import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import audio as audio_api
from app.api import chat as chat_api
from app.api import errors as errors_api
from app.api import exam as exam_api
from app.api import minimal_pairs as minimal_pairs_api
from app.api import phrases as phrases_api
from app.api import picture as picture_api
from app.api import prep as prep_api
from app.api import reflection as reflection_api
from app.api import scenarios as scenarios_api
from app.api import shadowing as shadowing_api
from app.api import stats as stats_api
from app.api import translate as translate_api
from app.api import words as words_api
from app.bot.handlers import router as bot_router
from app.bot.scheduler import init_scheduler, load_schedules_from_db
from app.config import get_settings
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
dp.include_router(bot_router)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    init_scheduler(bot)
    await load_schedules_from_db()

    # Set webhook to {WEBAPP_URL}/telegram/webhook
    webhook_url = f"{settings.webapp_url.rstrip('/')}/telegram/webhook"
    await bot.set_webhook(
        webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    logging.info("Webhook set to %s", webhook_url)

    yield

    await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(title="Lvaloda API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenarios_api.router)
app.include_router(chat_api.router)
app.include_router(exam_api.router)
app.include_router(audio_api.router)
app.include_router(words_api.router)
app.include_router(errors_api.router)
app.include_router(stats_api.router)
app.include_router(prep_api.router)
app.include_router(reflection_api.router)
app.include_router(shadowing_api.router)
app.include_router(minimal_pairs_api.router)
app.include_router(picture_api.router)
app.include_router(phrases_api.router)
app.include_router(translate_api.router)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/healthz")
async def healthz():
    return {"ok": True}
