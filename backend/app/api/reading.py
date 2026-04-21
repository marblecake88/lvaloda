"""Reading comprehension API — PMLP «Latvieši un līvi» first-task simulation.

Student silently reads one short text, then the examiner asks the 5 scripted
questions one by one. The text stays visible the whole time.
"""

from __future__ import annotations

import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assets.reading_texts import READING_TEXTS, READING_TOPICS
from app.auth.telegram import get_current_user
from app.db.models import ChatSession, Message, User
from app.db.session import get_session
from app.llm.chat import reading_final_report, reading_reply
from app.services import retrieval_service, stats_service

router = APIRouter(prefix="/api/reading", tags=["reading"])


_TEXTS_BY_ID: dict[str, dict] = {t["id"]: t for t in READING_TEXTS}


def _get_text(text_id: str) -> dict | None:
    return _TEXTS_BY_ID.get(text_id)


class StartReq(BaseModel):
    text_id: str  # id from READING_TEXTS (or "random")


class MessageReq(BaseModel):
    session_id: int
    text: str


class FinishReq(BaseModel):
    session_id: int


@router.get("/texts")
async def list_texts(_: User = Depends(get_current_user)):
    """Catalog for the picker screen. Returns all texts with a short preview."""
    items = []
    for t in READING_TEXTS:
        body = t["body"]
        preview = body.split("\n\n", 1)[0]
        if len(preview) > 200:
            preview = preview[:200].rstrip() + "…"
        items.append(
            {
                "id": t["id"],
                "title_lv": t["title_lv"],
                "topic": t["topic"],
                "topic_title_lv": READING_TOPICS.get(t["topic"], t["topic"]),
                "preview": preview,
                "source": t.get("source"),
            }
        )
    return {"topics": READING_TOPICS, "items": items}


@router.post("/start")
async def start_reading(
    req: StartReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if req.text_id == "random":
        text = random.choice(READING_TEXTS)
    else:
        text = _get_text(req.text_id)
        if not text:
            raise HTTPException(404, "reading text not found")

    session = ChatSession(user_id=user.id, mode="reading", scenario=text["id"])
    db.add(session)
    await db.commit()
    await db.refresh(session)

    level_hint = await retrieval_service.get_level_hint(db, user.id)

    greeting = await reading_reply(text, history=[], level_hint=level_hint)
    db.add(Message(session_id=session.id, role="assistant", content=greeting))
    await db.commit()

    return {
        "session_id": session.id,
        "text": {
            "id": text["id"],
            "title_lv": text["title_lv"],
            "topic": text["topic"],
            "topic_title_lv": READING_TOPICS.get(text["topic"], text["topic"]),
            "body": text["body"],
            "questions": text["questions"],
            "source": text.get("source"),
        },
        "reply": greeting,
    }


@router.post("/message")
async def reading_message(
    req: MessageReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session = await db.get(ChatSession, req.session_id)
    if not session or session.user_id != user.id or session.mode != "reading":
        raise HTTPException(404, "reading session not found")

    text = _get_text(session.scenario)
    if not text:
        raise HTTPException(500, "reading text missing")

    db.add(Message(session_id=session.id, role="user", content=req.text))
    await db.commit()

    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.id)
    )
    history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    level_hint = await retrieval_service.get_level_hint(db, user.id)

    reply = await reading_reply(text, history, level_hint=level_hint)
    db.add(Message(session_id=session.id, role="assistant", content=reply))
    await db.commit()

    await stats_service.record_message(db, user.id, topic=f"reading:{session.scenario}")

    return {"reply": reply}


@router.post("/finish")
async def finish_reading(
    req: FinishReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session = await db.get(ChatSession, req.session_id)
    if not session or session.user_id != user.id or session.mode != "reading":
        raise HTTPException(404, "reading session not found")

    text = _get_text(session.scenario)
    if not text:
        raise HTTPException(500, "reading text missing")

    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.id)
    )
    history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    level_hint = await retrieval_service.get_level_hint(db, user.id)

    report = await reading_final_report(text, history, level_hint=level_hint)

    from datetime import datetime

    session.finished_at = datetime.utcnow()
    await db.commit()

    return {
        "report": report,
        "text": {
            "id": text["id"],
            "title_lv": text["title_lv"],
            "questions": text["questions"],
        },
    }
