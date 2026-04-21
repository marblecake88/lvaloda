from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.db.models import ChatSession, Reflection, User
from app.db.session import get_session

router = APIRouter(prefix="/api/reflection", tags=["reflection"])


class ReflectionIn(BaseModel):
    session_id: int | None = None
    text: str


@router.post("")
async def save_reflection(
    body: ReflectionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    topic = None
    if body.session_id is not None:
        session = await db.get(ChatSession, body.session_id)
        if session and session.user_id == user.id:
            topic = session.scenario

    row = Reflection(
        user_id=user.id,
        session_id=body.session_id,
        text=body.text.strip()[:1000],
        topic=topic,
    )
    db.add(row)
    await db.commit()
    return {"ok": True}
