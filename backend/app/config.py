from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    bot_token: str
    webapp_url: str

    xai_api_key: str
    xai_model: str = "grok-4-fast"
    xai_image_model: str = "grok-imagine-image"

    openai_api_key: str
    openai_stt_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "nova"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./lvaloda.db"

    default_reminder_time: str = "19:00"
    timezone: str = "Europe/Riga"


@lru_cache
def get_settings() -> Settings:
    return Settings()
