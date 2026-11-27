from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    gemini_api_key: SecretStr | None = None
    DEFAULT_PROVIDER: str = "google_genai"
    GEMINI_MODEL: str = "gemini-3.6-flash"

    gemini_api_key: SecretStr | None = None
    DEFAULT_PROVIDER="google_genai"
    GEMINI_MODEL="gemini-3.6-flash"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:    
    return Settings()