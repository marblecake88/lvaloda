"""Picture-description mode: scene catalog, generation, persistent cache."""

import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assets.pictures import SCENES, generate_image_b64, scene_by_key
from app.auth.telegram import get_current_user
from app.db.models import ChatSession, GeneratedPicture, Message, UnnaturalPhrase, User
from app.db.session import get_session
from app.llm.chat import analyze_picture

router = APIRouter(prefix="/api/picture", tags=["picture"])


def _to_summary(p: GeneratedPicture) -> dict:
    return {
        "id": p.id,
        "scene_key": p.scene_key,
        "topic_lv": p.topic_lv,
        "topic_ru": p.topic_ru,
        "prompt_lv": p.prompt_lv,
        "image_url": f"data:image/png;base64,{p.image_b64}",
        "created_at": p.created_at.isoformat(),
    }


@router.get("/scenes")
async def list_scenes(_user: User = Depends(get_current_user)):
    """Available themes the user can request a new generation for."""
    return {
        "scenes": [
            {"key": s.key, "topic_lv": s.topic_lv, "topic_ru": s.topic_ru}
            for s in SCENES
        ]
    }


@router.get("/history")
async def list_history(
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    rows = (
        await db.execute(
            select(GeneratedPicture)
            .where(GeneratedPicture.user_id == user.id)
            .order_by(GeneratedPicture.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {"pictures": [_to_summary(p) for p in rows]}


class GenerateReq(BaseModel):
    scene_key: str | None = None  # None → random


@router.post("/generate")
async def generate(
    body: GenerateReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    scene = scene_by_key(body.scene_key) if body.scene_key else random.choice(SCENES)
    if scene is None:
        raise HTTPException(404, "scene not found")

    b64 = await generate_image_b64(scene.image_prompt)

    row = GeneratedPicture(
        user_id=user.id,
        scene_key=scene.key,
        topic_lv=scene.topic_lv,
        topic_ru=scene.topic_ru,
        prompt_lv=scene.prompt_lv,
        image_b64=b64,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_summary(row)


@router.get("/{picture_id}")
async def fetch(
    picture_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(GeneratedPicture, picture_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "not found")
    return _to_summary(row)


@router.delete("/{picture_id}")
async def remove(
    picture_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(GeneratedPicture, picture_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


class FinishReq(BaseModel):
    session_id: int
    picture_id: int


@router.post("/finish")
async def finish_picture(
    req: FinishReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session = await db.get(ChatSession, req.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "session not found")

    picture = await db.get(GeneratedPicture, req.picture_id)
    if not picture or picture.user_id != user.id:
        raise HTTPException(404, "picture not found")

    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.id)
    )
    history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    data_url = f"data:image/png;base64,{picture.image_b64}"
    report = await analyze_picture(data_url, history)

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

    session.finished_at = datetime.utcnow()
    await db.commit()

    return {"report": report}
