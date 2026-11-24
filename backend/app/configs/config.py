from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


Provider = Literal["google_genai", "groq", "openai"]


class AgentModel(BaseModel):
    provider: Provider
    model: str


class Settings(BaseSettings):
    gemini_api_key: SecretStr | None = None
    gemini_api_key_fallback_1: SecretStr | None = None  # Optional key
    groq_api_key: SecretStr | None = None
    groq_api_key_fallback_1: SecretStr | None = None 
    openai_api_key: SecretStr | None = None

    default_provider: Provider = "google_genai"
    gemini_model: str = "gemini-3.5-flash"
    groq_model: str = "qwen/qwen3.8-27b"
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache()
def get_settings() -> Settings:    
    return Settings()