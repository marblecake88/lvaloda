"""Parse the `💡 Dabiskāk: "better" (note)` block out of assistant replies
and persist it to UnnaturalPhrase so it can feed Vocabulary and the weekly
summary without extra LLM calls.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatSession, UnnaturalPhrase

log = logging.getLogger(__name__)

# The model might emit any of: curly or straight quotes, « », optional trailing
# period inside the parens. The note is everything inside the last () on that
# line. Example match:
#   💡 Dabiskāk: "Man ir brālis un māsa" (по-русски: "есть" + N.nom в Lat)
_PATTERN = re.compile(
    r"💡\s*Dabiskāk[:：]\s*[\"«]?(.+?)[\"»]?\s*(?:\(([^)]+)\))?\s*$",
    re.MULTILINE,
)


def parse_dabiskak(assistant_text: str) -> tuple[str, str | None] | None:
    """Return (better_phrase, note_ru) if a Dabiskāk block is present."""
    match = _PATTERN.search(assistant_text)
    if not match:
        return None
    better = match.group(1).strip().strip('"«»')
    note = (match.group(2) or "").strip() or None
    if not better:
        return None
    return better, note


async def extract_and_save(
    db: AsyncSession,
    *,
    assistant_text: str,
    last_user_text: str,
    session: ChatSession,
) -> UnnaturalPhrase | None:
    """Called after each assistant reply in dialog mode."""
    parsed = parse_dabiskak(assistant_text)
    if parsed is None:
        return None
    better, note = parsed
    row = UnnaturalPhrase(
        user_id=session.user_id,
        session_id=session.id,
        said=last_user_text[:500],
        better=better[:500],
        note_ru=note,
        topic=session.scenario,
    )
    db.add(row)
    try:
        await db.commit()
    except Exception:
        log.exception("Failed to save UnnaturalPhrase")
        await db.rollback()
        return None
    return row
