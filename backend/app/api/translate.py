"""Russian ↔ Latvian translator.

Auto-detects the source language and returns a natural translation in the
other. Accepts text or audio input (audio is first transcribed by Whisper
with auto-language detection).
"""

import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.telegram import get_current_user
from app.config import get_settings
from app.db.models import User
from app.llm.client import grok, openai

log = logging.getLogger(__name__)
_settings = get_settings()

router = APIRouter(prefix="/api/translate", tags=["translate"])


_TRANSLATE_PROMPT = """You are a Russian–Latvian translator for a living app.

Input is either Russian or Latvian. Auto-detect which.

Output STRICT JSON (no markdown wrapper):
{"source_lang": "ru" | "lv", "translation": "<natural translation into the OTHER language>"}

Translation style:
- Natural everyday speech, as a real person would say it in 2025 (NOT textbook).
- Grammatically correct, but conversational and warm.
- Keep the same register (casual stays casual, formal stays formal).
- If the input is Latvian → translate to Russian.
- If the input is Russian → translate to Latvian (use natural Rīga spoken Latvian with
  particles like "nu, jau, vai ne" where they fit — avoid literary forms when a
  common everyday word works).
- No notes, no comments, just source_lang + translation.

Input:
"""


async def _translate(text: str) -> dict:
    if not text.strip():
        raise HTTPException(400, "empty input")
    resp = await grok.chat.completions.create(
        model=_settings.xai_model,
        messages=[
            {"role": "user", "content": _TRANSLATE_PROMPT + text.strip()},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(502, f"LLM returned non-JSON: {raw[:200]}")

    return {
        "source_lang": data.get("source_lang") or "?",
        "source_text": text.strip(),
        "translation": (data.get("translation") or "").strip(),
    }


class TextIn(BaseModel):
    text: str


@router.post("/text")
async def translate_text(
    body: TextIn,
    _user: User = Depends(get_current_user),
):
    return await _translate(body.text)


@router.post("/audio")
async def translate_audio(
    file: UploadFile = File(...),
    _user: User = Depends(get_current_user),
):
    data = await file.read()
    # Auto-detect language (no `language` hint): Whisper picks up RU/LV fine.
    try:
        tx = await openai.audio.transcriptions.create(
            model=_settings.openai_stt_model,
            file=(file.filename or "audio.webm", data),
            temperature=0,
        )
    except Exception as e:
        log.exception("translate: STT failed")
        raise HTTPException(502, f"STT failed: {type(e).__name__}")

    text = (tx.text or "").strip()
    if not text:
        raise HTTPException(400, "empty transcription")
    return await _translate(text)
