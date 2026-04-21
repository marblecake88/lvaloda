from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
async def summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await stats_service.summary(db, user.id)


@router.get("/weekly")
async def weekly(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await stats_service.weekly_report(db, user.id)
