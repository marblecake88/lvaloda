"""Telegram Mini App initData verification.

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.db.session import get_session


def _parse_init_data(init_data: str, bot_token: str) -> dict:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad initData hash")

    user_json = parsed.get("user")
    if not user_json:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no user in initData")

    return json.loads(user_json)


async def get_current_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_session),
) -> User:
    settings = get_settings()
    tg_user = _parse_init_data(x_telegram_init_data, settings.bot_token)

    tg_id = int(tg_user["id"])
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        telegram_id=tg_id,
        username=tg_user.get("username"),
        first_name=tg_user.get("first_name"),
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError:
        # Concurrent request won the race — re-fetch the committed row.
        await db.rollback()
        result = await db.execute(select(User).where(User.telegram_id == tg_id))
        return result.scalar_one()
