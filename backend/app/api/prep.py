"""Pre-task planning endpoint: 5 useful lexical chunks + quick preview for a topic.

Evidence: SLA research shows that even 60 seconds of pre-task planning
significantly improves fluency and complexity on speaking tasks (Ellis, Skehan).
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.telegram import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.llm.client import grok
from app.llm.scenarios import get_scenario
from app.config import get_settings

router = APIRouter(prefix="/api/prep", tags=["prep"])

_settings = get_settings()

_PREP_PROMPT = """Сгенерируй для ученика A2-B1 латышского набор полезных материалов \
для разговора на тему "{title_lv}" ({title_ru}).

КРИТИЧЕСКИ ВАЖНО про стиль:
- Все материалы должны звучать так, как реально говорят в Риге 2025 — живо, \
разговорно, не по-учебнику.
- Грамматически правильно, но НЕ книжно. Предпочтение повседневной лексике и \
естественным оборотам (с частицами типа «nu», «vai ne», «jau» где уместно).
- Если есть выбор между литературной и разговорной формой — выбирай разговорную.

Верни СТРОГО JSON без markdown-обёртки:
{{
  "chunks": [
    {{"lv": "готовая живая разговорная фраза на латышском", "ru": "перевод"}}
  ],
  "key_words": ["vārds1", "vārds2", "vārds3", "vārds4", "vārds5"],
  "sample_angles": ["угол1 для разговора", "угол2", "угол3"]
}}

Требования:
- chunks: ровно 5 готовых разговорных формул (не отдельные слова! фразы), которые \
ученик может выучить целиком и встроить в живую беседу. Такие, которые действительно \
произносят в обычной речи.
- key_words: 5 ключевых существительных/глаголов по теме — частоупотребимые в живом \
общении.
- sample_angles: 3 подсказки «о чём могут спросить» — короткие формулировки на русском."""


@router.get("/{scenario_key}")
async def prep_for(
    scenario_key: str,
    _user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_session),
):
    scenario = get_scenario(scenario_key)
    if not scenario:
        raise HTTPException(404, "scenario not found")

    prompt = _PREP_PROMPT.format(
        title_lv=scenario.title_lv, title_ru=scenario.title_ru
    )
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"chunks": [], "key_words": [], "sample_angles": []}

    return {
        "scenario": {
            "key": scenario.key,
            "title_lv": scenario.title_lv,
            "title_ru": scenario.title_ru,
        },
        "chunks": data.get("chunks", [])[:5],
        "key_words": data.get("key_words", [])[:5],
        "sample_angles": data.get("sample_angles", [])[:3],
    }
