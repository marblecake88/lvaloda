import random

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.assets.minimal_pairs import PAIRS
from app.auth.telegram import get_current_user
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/api/minimal-pairs", tags=["minimal-pairs"])


@router.get("/next")
async def next_pair(
    _user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_session),
):
    pair = random.choice(PAIRS)
    # randomize which side plays first for the quiz
    correct = random.choice(["a", "b"])
    return {
        "a": pair.a,
        "b": pair.b,
        "a_ru": pair.a_ru,
        "b_ru": pair.b_ru,
        "note_ru": pair.note_ru,
        "correct": correct,
    }
