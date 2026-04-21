"""Spaced retrieval + adaptive difficulty inputs to the LLM."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SavedWord, TopicSession, UnnaturalPhrase


async def get_known_vocab(db: AsyncSession, user_id: int, limit: int = 15) -> list[str]:
    """Short bag-of-words hint to the LLM.

    Only individual words / short 2-word collocations pass the filter —
    passing full "better" phrases from UnnaturalPhrase to the system prompt
    confuses the model (it treats them as literal examples to reproduce)
    and can leak them into the reply. Keep it minimal.
    """
    words = (
        await db.execute(
            select(SavedWord.word_lv)
            .where(SavedWord.user_id == user_id)
            .order_by(SavedWord.created_at.desc())
            .limit(30)
        )
    ).scalars().all()

    combined: list[str] = []
    seen: set[str] = set()
    for item in words:
        token = (item or "").strip()
        if not token:
            continue
        # Skip long phrases — only single words or 2-word collocations.
        if len(token.split()) > 2 or len(token) > 30:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        combined.append(token)
        if len(combined) >= limit:
            break
    return combined


async def get_level_hint(db: AsyncSession, user_id: int) -> str:
    """Map the user's recent fluency_scores to a short coaching hint."""
    scores = (
        await db.execute(
            select(TopicSession.fluency_score)
            .where(
                TopicSession.user_id == user_id,
                TopicSession.fluency_score.is_not(None),
            )
            .order_by(TopicSession.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    if not scores:
        return "новичок: держи язык простым, A2-лексика, короткие предложения"
    avg = sum(scores) / len(scores)
    if avg < 2.5:
        return "начинающий: простые предложения, A2-лексика, короткие реплики"
    if avg < 3.5:
        return "средний: обычная беседа, привычная лексика, не усложняй"
    return "уверенный: усложняй — гипотетика, абстрактные мнения, сравнения"
