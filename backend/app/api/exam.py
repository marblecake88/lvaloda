"""Exam simulation API with anti-repeat angles."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.db.models import ChatSession, Message, TopicSession, User
from app.db.session import get_session
from app.llm.chat import exam_final_report, exam_reply
from app.llm.scenarios import EXAM_TOPICS, get_scenario
from app.services import retrieval_service, stats_service

router = APIRouter(prefix="/api/exam", tags=["exam"])


class StartReq(BaseModel):
    topic: str  # scenario key from EXAM_TOPICS (or "random")


class MessageReq(BaseModel):
    session_id: int
    text: str


class FinishReq(BaseModel):
    session_id: int


class RepeatReq(BaseModel):
    session_id: int


async def _covered_angles_for(db: AsyncSession, user: User, topic_key: str) -> list[str]:
    result = await db.execute(
        select(TopicSession).where(
            TopicSession.user_id == user.id, TopicSession.topic == topic_key
        )
    )
    angles: set[str] = set()
    for s in result.scalars().all():
        for a in s.covered_angles or []:
            angles.add(a)
    return sorted(angles)


@router.post("/start")
async def start_exam(
    req: StartReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if req.topic == "random":
        import random

        scenario = random.choice(EXAM_TOPICS)
    else:
        scenario = get_scenario(req.topic)
        if not scenario or scenario.kind != "exam":
            raise HTTPException(404, "exam topic not found")

    covered = await _covered_angles_for(db, user, scenario.key)

    session = ChatSession(user_id=user.id, mode="exam", scenario=scenario.key)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    known_vocab = await retrieval_service.get_known_vocab(db, user.id)
    level_hint = await retrieval_service.get_level_hint(db, user.id)

    first_question = await exam_reply(
        scenario,
        covered,
        history=[],
        known_vocab=known_vocab,
        level_hint=level_hint,
    )
    db.add(Message(session_id=session.id, role="assistant", content=first_question))
    await db.commit()

    return {
        "session_id": session.id,
        "topic": {"key": scenario.key, "title_lv": scenario.title_lv, "title_ru": scenario.title_ru},
        "reply": first_question,
        "covered_angles": covered,
    }


@router.post("/message")
async def exam_message(
    req: MessageReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session = await db.get(ChatSession, req.session_id)
    if not session or session.user_id != user.id or session.mode != "exam":
        raise HTTPException(404, "exam session not found")

    scenario = get_scenario(session.scenario)
    if not scenario:
        raise HTTPException(500, "scenario missing")

    covered = await _covered_angles_for(db, user, scenario.key)

    db.add(Message(session_id=session.id, role="user", content=req.text))
    await db.commit()

    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.id)
    )
    history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    known_vocab = await retrieval_service.get_known_vocab(db, user.id)
    level_hint = await retrieval_service.get_level_hint(db, user.id)

    reply = await exam_reply(
        scenario,
        covered,
        history,
        known_vocab=known_vocab,
        level_hint=level_hint,
    )
    db.add(Message(session_id=session.id, role="assistant", content=reply))
    await db.commit()

    await stats_service.record_message(db, user.id, topic=session.scenario)

    return {"reply": reply}


@router.post("/finish")
async def finish_exam(
    req: FinishReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session = await db.get(ChatSession, req.session_id)
    if not session or session.user_id != user.id or session.mode != "exam":
        raise HTTPException(404, "exam session not found")

    scenario = get_scenario(session.scenario)
    if not scenario:
        raise HTTPException(500, "scenario missing")

    covered = await _covered_angles_for(db, user, scenario.key)

    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.id)
    )
    history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    known_vocab = await retrieval_service.get_known_vocab(db, user.id)
    level_hint = await retrieval_service.get_level_hint(db, user.id)

    report = await exam_final_report(
        scenario,
        covered,
        history,
        known_vocab=known_vocab,
        level_hint=level_hint,
    )

    ts = TopicSession(
        user_id=user.id,
        topic=scenario.key,
        covered_angles=report.get("covered_angles", []),
        fluency_score=report.get("fluency_score"),
        report=report,
    )
    db.add(ts)

    from datetime import datetime

    session.finished_at = datetime.utcnow()
    await db.commit()

    return {"report": report, "previously_covered": covered}


@router.post("/repeat")
async def repeat_exam(
    req: RepeatReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Task repetition: same topic, fresh session. Evidence from SLA research
    (Bygate et al.) — repeating a speaking task within 24h yields significant
    fluency gains on the second attempt.
    """
    prev = await db.get(ChatSession, req.session_id)
    if not prev or prev.user_id != user.id or prev.mode != "exam":
        raise HTTPException(404, "exam session not found")

    scenario = get_scenario(prev.scenario)
    if not scenario:
        raise HTTPException(500, "scenario missing")

    covered = await _covered_angles_for(db, user, scenario.key)

    session = ChatSession(user_id=user.id, mode="exam", scenario=scenario.key)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    known_vocab = await retrieval_service.get_known_vocab(db, user.id)
    level_hint = await retrieval_service.get_level_hint(db, user.id)

    first_question = await exam_reply(
        scenario,
        covered,
        history=[],
        known_vocab=known_vocab,
        level_hint=level_hint,
    )
    db.add(Message(session_id=session.id, role="assistant", content=first_question))
    await db.commit()

    return {
        "session_id": session.id,
        "topic": {
            "key": scenario.key,
            "title_lv": scenario.title_lv,
            "title_ru": scenario.title_ru,
        },
        "reply": first_question,
        "covered_angles": covered,
    }
