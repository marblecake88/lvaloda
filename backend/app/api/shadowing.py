"""Shadowing mode: listen → repeat → compare.

Research: shadowing (immediate imitation of native speech) significantly
improves pronunciation, prosody and listening comprehension for A2-B1.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.config import get_settings
from app.db.models import ShadowingSession, User
from app.db.session import get_session
from app.llm.audio import synthesize
from app.llm.client import grok
from app.llm.scenarios import EXAM_TOPICS, get_scenario

router = APIRouter(prefix="/api/shadowing", tags=["shadowing"])

_settings = get_settings()

_PHRASES_PROMPT = """Сгенерируй для ученика A2-B1 латышского 8 коротких фраз на тему \
"{title_lv}" ({title_ru}) для упражнения shadowing (слушать и повторять за носителем).

КРИТИЧЕСКИ ВАЖНО про стиль:
- Это должны быть фразы, которые реально произносят люди в Риге 2025 — живые, \
разговорные, не из учебника.
- Грамматически правильно, но интонация живая: допускаются частицы (nu, jau, vai ne?, \
tad jau, taču), короткие формы, естественные вопросы-хвосты.
- Лексика — повседневная, частоупотребимая. Избегай редких литературных слов.

Требования:
- Каждая фраза 5-10 слов.
- Разного типа: утверждение, вопрос, реакция-восклицание, короткая реплика ответа.
- Постепенно от простых к чуть посложнее.

Верни СТРОГО JSON без markdown:
{{"phrases": [{{"lv": "...", "ru": "перевод"}}]}}"""


class StartReq(BaseModel):
    topic: str | None = None  # scenario key; если пусто — random из EXAM_TOPICS


@router.post("/start")
async def start_shadowing(
    body: StartReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if body.topic:
        scenario = get_scenario(body.topic)
        if not scenario:
            raise HTTPException(404, "topic not found")
    else:
        import random

        scenario = random.choice(EXAM_TOPICS)

    prompt = _PHRASES_PROMPT.format(
        title_lv=scenario.title_lv, title_ru=scenario.title_ru
    )
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    phrases = (data.get("phrases") or [])[:8]

    if not phrases:
        raise HTTPException(500, "LLM failed to generate phrases")

    session = ShadowingSession(
        user_id=user.id,
        topic=scenario.key,
        phrases=phrases,
        progress_idx=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "session_id": session.id,
        "topic": {
            "key": scenario.key,
            "title_lv": scenario.title_lv,
            "title_ru": scenario.title_ru,
        },
        "phrases": phrases,
    }


@router.get("/{session_id}/tts/{idx}")
async def shadowing_tts(
    session_id: int,
    idx: int,
    speed: float = 1.0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session = await db.get(ShadowingSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "not found")
    if idx < 0 or idx >= len(session.phrases):
        raise HTTPException(400, "bad index")
    text = session.phrases[idx].get("lv", "")
    if not text:
        raise HTTPException(400, "empty phrase")
    audio = await synthesize(text, speed=speed)
    return Response(content=audio, media_type="audio/mpeg")
