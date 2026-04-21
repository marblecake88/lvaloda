from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.db.models import SavedWord, User
from app.db.session import get_session

router = APIRouter(prefix="/api/words", tags=["words"])


class WordIn(BaseModel):
    word_lv: str
    translation_ru: str
    example: str | None = None
    topic: str | None = None


class WordOut(BaseModel):
    id: int
    word_lv: str
    translation_ru: str
    example: str | None
    topic: str | None
    created_at: str


@router.get("", response_model=list[WordOut])
async def list_words(
    topic: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    q = select(SavedWord).where(SavedWord.user_id == user.id)
    if topic:
        q = q.where(SavedWord.topic == topic)
    q = q.order_by(SavedWord.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return [
        WordOut(
            id=r.id,
            word_lv=r.word_lv,
            translation_ru=r.translation_ru,
            example=r.example,
            topic=r.topic,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("", response_model=WordOut)
async def add_word(
    body: WordIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = SavedWord(
        user_id=user.id,
        word_lv=body.word_lv.strip(),
        translation_ru=body.translation_ru.strip(),
        example=(body.example or "").strip() or None,
        topic=body.topic,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return WordOut(
        id=row.id,
        word_lv=row.word_lv,
        translation_ru=row.translation_ru,
        example=row.example,
        topic=row.topic,
        created_at=row.created_at.isoformat(),
    )


@router.delete("/{word_id}")
async def delete_word(
    word_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(SavedWord, word_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}
