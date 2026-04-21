from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assets.top_phrases import all_categories, phrases_in
from app.auth.telegram import get_current_user
from app.db.models import PhraseRun, User
from app.db.session import get_session

router = APIRouter(prefix="/api/phrases", tags=["phrases"])


@router.get("/categories")
async def categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Categories with the most-recent run stat attached to each."""
    # Best run per category (highest known/total ratio in last 10 runs)
    cats = all_categories()
    # Build latest-run map in one query per category (cheap; few categories).
    for c in cats:
        last_run = (
            await db.execute(
                select(PhraseRun)
                .where(
                    PhraseRun.user_id == user.id,
                    PhraseRun.category == c["key"],
                )
                .order_by(PhraseRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last_run:
            c["last_run"] = {
                "known": last_run.known_count,
                "total": last_run.total,
                "at": last_run.created_at.isoformat(),
            }
        else:
            c["last_run"] = None
    return {"categories": cats}


@router.get("/{category}")
async def phrases(
    category: str, _user: User = Depends(get_current_user)
):
    items = phrases_in(category)
    if not items:
        raise HTTPException(404, "category not found")
    return {"category": category, "items": items}


@router.get("/{category}/runs")
async def category_runs(
    category: str,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    rows = (
        await db.execute(
            select(PhraseRun)
            .where(PhraseRun.user_id == user.id, PhraseRun.category == category)
            .order_by(PhraseRun.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "runs": [
            {
                "id": r.id,
                "total": r.total,
                "known": r.known_count,
                "duration_sec": r.duration_sec,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


class RunReq(BaseModel):
    category: str
    total: int
    known: int
    duration_sec: int | None = None


@router.post("/run")
async def save_run(
    body: RunReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = PhraseRun(
        user_id=user.id,
        category=body.category,
        total=body.total,
        known_count=body.known,
        duration_sec=body.duration_sec,
    )
    db.add(row)
    await db.commit()
    return {"ok": True, "id": row.id}
