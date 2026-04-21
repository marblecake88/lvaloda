"""Dialog mode chat API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.db.models import ChatSession, Message, UnnaturalPhrase, User
from app.db.session import get_session
from app.llm.chat import analyze_dialog, dialog_reply, russian_hint
from app.llm.scenarios import get_scenario
from app.services import retrieval_service, stats_service, unnatural_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class StartReq(BaseModel):
    scenario: str


class MessageReq(BaseModel):
    session_id: int
    text: str


class HintReq(BaseModel):
    text: str


class FinishReq(BaseModel):
    session_id: int


@router.post("/start")
async def start_session(
    req: StartReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    scenario = get_scenario(req.scenario)
    if not scenario:
        raise HTTPException(404, "scenario not found")

    session = ChatSession(user_id=user.id, mode="dialog", scenario=scenario.key)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    known_vocab = await retrieval_service.get_known_vocab(db, user.id)
    level_hint = await retrieval_service.get_level_hint(db, user.id)

    assistant_text = await dialog_reply(
        scenario,
        history=[],
        known_vocab=known_vocab,
        level_hint=level_hint,
    )
    msg = Message(session_id=session.id, role="assistant", content=assistant_text)
    db.add(msg)
    await db.commit()

    return {"session_id": session.id, "reply": assistant_text}


@router.post("/message")
async def send_message(
    req: MessageReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session = await db.get(ChatSession, req.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "session not found")

    scenario = get_scenario(session.scenario)
    if not scenario:
        raise HTTPException(500, "scenario missing")

    db.add(Message(session_id=session.id, role="user", content=req.text))
    await db.commit()

    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.id)
    )
    history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    known_vocab = await retrieval_service.get_known_vocab(db, user.id)
    level_hint = await retrieval_service.get_level_hint(db, user.id)

    assistant_text = await dialog_reply(
        scenario,
        history,
        known_vocab=known_vocab,
        level_hint=level_hint,
    )
    db.add(Message(session_id=session.id, role="assistant", content=assistant_text))
    await db.commit()

    # Post-reply side effects: auto-extract Dabiskāk block + track daily stats.
    await unnatural_service.extract_and_save(
        db,
        assistant_text=assistant_text,
        last_user_text=req.text,
        session=session,
    )
    await stats_service.record_message(db, user.id, topic=session.scenario)

    return {"reply": assistant_text}


@router.post("/hint")
async def get_hint(req: HintReq, _user: User = Depends(get_current_user)):
    return {"hint": await russian_hint(req.text)}


@router.post("/finish")
async def finish_chat(
    req: FinishReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """End a dialog session and return an analysis report."""
    session = await db.get(ChatSession, req.session_id)
    if not session or session.user_id != user.id or session.mode != "dialog":
        raise HTTPException(404, "dialog session not found")

    scenario = get_scenario(session.scenario)
    if not scenario:
        raise HTTPException(500, "scenario missing")

    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.id)
    )
    msgs = result.scalars().all()
    if len(msgs) < 2:
        raise HTTPException(400, "session too short to analyse")
    history = [{"role": m.role, "content": m.content} for m in msgs]

    report = await analyze_dialog(scenario, history)

    # Persist the analysis-found phrases alongside the per-message auto-logged ones.
    for p in report.get("unnatural_phrases", []) or []:
        said = (p.get("said") or "").strip()
        better = (p.get("better") or "").strip()
        if not said or not better:
            continue
        db.add(
            UnnaturalPhrase(
                user_id=user.id,
                session_id=session.id,
                said=said[:500],
                better=better[:500],
                note_ru=(p.get("note_ru") or "").strip() or None,
                topic=session.scenario,
            )
        )

    from datetime import datetime

    session.finished_at = datetime.utcnow()
    await db.commit()

    return {"report": report}
