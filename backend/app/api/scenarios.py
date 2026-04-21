from fastapi import APIRouter, Depends

from app.auth.telegram import get_current_user
from app.db.models import User
from app.llm.scenarios import DAILY_SITUATIONS, EXAM_TOPICS

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("")
async def list_scenarios(_user: User = Depends(get_current_user)):
    return {
        "exam": [
            {"key": s.key, "title_lv": s.title_lv, "title_ru": s.title_ru}
            for s in EXAM_TOPICS
        ],
        "daily": [
            {"key": s.key, "title_lv": s.title_lv, "title_ru": s.title_ru}
            for s in DAILY_SITUATIONS
        ],
    }
