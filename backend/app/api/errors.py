from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.db.models import UnnaturalPhrase, User
from app.db.session import get_session

router = APIRouter(prefix="/api/errors", tags=["errors"])


@router.get("")
async def list_errors(
    limit: int = 100,
    topic: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    q = select(UnnaturalPhrase).where(UnnaturalPhrase.user_id == user.id)
    if topic:
        q = q.where(UnnaturalPhrase.topic == topic)
    q = q.order_by(UnnaturalPhrase.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "said": r.said,
            "better": r.better,
            "note_ru": r.note_ru,
            "topic": r.topic,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.delete("/{error_id}")
async def delete_error(
    error_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(UnnaturalPhrase, error_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}
