"""STT (Whisper) and TTS via OpenAI."""

import logging
import re
from io import BytesIO

from app.config import get_settings
from app.llm.client import openai
from app.llm.scenarios import Scenario

log = logging.getLogger(__name__)
_settings = get_settings()

# Strips **bold**, *italics*, trailing Dabiskāk block, stray markdown that TTS
# would otherwise read aloud as "asterisk".
_MARKDOWN = re.compile(r"\*+")
_DABISKAK = re.compile(r"💡\s*Dabiskāk.*$", re.DOTALL)

# Whisper sometimes transliterates Latvian to Cyrillic for speakers with a
# Russian accent, even when language="lv" is set. We detect, retry with a
# stronger prompt, and as a last resort transliterate back.
_CYRILLIC = re.compile(r"[\u0400-\u04FF]")

# Best-effort Cyrillic -> Latin Latvian mapping.
# Long vowels are impossible to infer without the audio — we output short
# forms and the user can edit the transcript before sending.
_CYR_TO_LV = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
        "е": "e", "ё": "jo", "ж": "ž", "з": "z", "и": "i",
        "й": "j", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "č",
        "ш": "š", "щ": "šč", "ъ": "", "ы": "i", "ь": "",
        "э": "e", "ю": "ju", "я": "ja",
        "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D",
        "Е": "E", "Ё": "Jo", "Ж": "Ž", "З": "Z", "И": "I",
        "Й": "J", "К": "K", "Л": "L", "М": "M", "Н": "N",
        "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
        "У": "U", "Ф": "F", "Х": "H", "Ц": "C", "Ч": "Č",
        "Ш": "Š", "Щ": "Šč", "Ъ": "", "Ы": "I", "Ь": "",
        "Э": "E", "Ю": "Ju", "Я": "Ja",
    }
)


def _cyrillic_to_latvian(text: str) -> str:
    return text.translate(_CYR_TO_LV)


def _build_whisper_prompt(scenario: Scenario | None) -> str:
    """Bias Whisper towards Latvian vocabulary and the current scenario.

    Whisper's `prompt` param (up to 224 tokens) nudges the model on
    spelling, vocabulary and style — a short natural-Latvian sentence
    with scenario-specific words works better than a list of keywords.
    """
    base = (
        "Šī ir ikdienas saruna latviešu valodā ar garumzīmēm un mīkstinājuma "
        "zīmēm: ā, ē, ī, ō, ū, č, š, ž, ņ, ļ, ķ, ģ."
    )
    if scenario is None:
        return base
    return f"{base} Saruna par tēmu: {scenario.title_lv}. {scenario.context}"


_STRICT_LATIN_PROMPT = (
    "Šī ir saruna latviešu valodā. Raksti transkripciju TIKAI ar latīņu burtiem "
    "un latviešu diakritiku: ā, ē, ī, ō, ū, č, š, ž, ņ, ļ, ķ, ģ. "
    "NEKAD nelieto kirilicu (русские буквы)."
)


async def transcribe(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    scenario: Scenario | None = None,
) -> str:
    resp = await openai.audio.transcriptions.create(
        model=_settings.openai_stt_model,
        file=(filename, audio_bytes),
        language="lv",
        prompt=_build_whisper_prompt(scenario),
        temperature=0,
    )
    text = resp.text or ""

    # Whisper slipped into Cyrillic transliteration — retry with a stricter prompt.
    if _CYRILLIC.search(text):
        log.info("STT: Cyrillic detected in output, retrying with strict-Latin prompt")
        try:
            resp2 = await openai.audio.transcriptions.create(
                model=_settings.openai_stt_model,
                file=(filename, audio_bytes),
                language="lv",
                prompt=_STRICT_LATIN_PROMPT,
                temperature=0.2,
            )
            text2 = resp2.text or ""
            if text2 and not _CYRILLIC.search(text2):
                return text2
            # Still cyrillic on retry → transliterate best-effort.
            log.warning("STT: retry still returned Cyrillic, transliterating")
            return _cyrillic_to_latvian(text2 or text)
        except Exception:
            log.exception("STT retry failed, transliterating original")
            return _cyrillic_to_latvian(text)
    return text


async def synthesize(text: str, speed: float = 1.0) -> bytes:
    # OpenAI TTS API accepts speed 0.25..4.0 and has a ~4096-char input cap.
    speed = max(0.5, min(2.0, speed))
    raw = (text or "").strip()
    # Strip markdown and any trailing Dabiskāk block so TTS doesn't say "zvaigznīte".
    clean = _DABISKAK.sub("", raw)
    clean = _MARKDOWN.sub("", clean).strip()
    if len(clean) > 4000:
        clean = clean[:4000]
    if not clean:
        raise ValueError("empty text for TTS")
    resp = await openai.audio.speech.create(
        model=_settings.openai_tts_model,
        voice=_settings.openai_tts_voice,
        input=clean,
        response_format="mp3",
        speed=speed,
    )
    # openai SDK 2.x returns a binary response wrapper whose `iter_bytes()` is
    # a SYNC generator even on the async client. Prefer `aread`/`aiter_bytes`
    # when available, and fall back to sync iteration otherwise.
    if hasattr(resp, "aread"):
        return await resp.aread()
    if hasattr(resp, "aiter_bytes"):
        buf = BytesIO()
        async for chunk in resp.aiter_bytes():
            buf.write(chunk)
        return buf.getvalue()
    buf = BytesIO()
    for chunk in resp.iter_bytes():
        buf.write(chunk)
    return buf.getvalue()
