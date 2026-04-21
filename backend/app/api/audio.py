import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.auth.telegram import get_current_user
from app.db.models import User
from app.llm.audio import synthesize, transcribe
from app.llm.scenarios import get_scenario

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.post("/stt")
async def stt(
    file: UploadFile = File(...),
    scenario: str | None = Form(None),
    _user: User = Depends(get_current_user),
):
    data = await file.read()
    scenario_obj = get_scenario(scenario) if scenario else None
    text = await transcribe(
        data,
        filename=file.filename or "audio.webm",
        scenario=scenario_obj,
    )
    return {"text": text}


@router.post("/tts")
async def tts(
    text: str = Form(...),
    speed: float = Form(1.0),
    _user: User = Depends(get_current_user),
):
    try:
        audio = await synthesize(text, speed=speed)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.exception("TTS failed (input head=%r)", text[:120])
        # Bubble up the real OpenAI error message so the frontend can show it.
        raise HTTPException(502, f"{type(e).__name__}: {str(e)[:240]}")
    return Response(content=audio, media_type="audio/mpeg")
