"""LLM clients: xAI Grok (via OpenAI-compatible SDK) + OpenAI for STT/TTS."""

from openai import AsyncOpenAI

from app.config import get_settings

_settings = get_settings()

grok = AsyncOpenAI(
    api_key=_settings.xai_api_key,
    base_url="https://api.x.ai/v1",
)

openai = AsyncOpenAI(api_key=_settings.openai_api_key)
