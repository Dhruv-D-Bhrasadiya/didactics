from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env.

    The settings include provider credentials and default model selections.
    Pydantic validates values and masks secret keys when represented.

    Example:
        settings = Settings(default_provider="groq")
    """
    # SecretStr masks the keys in logs/print statements
    gemini_api_key: SecretStr | None = None
    gemini_api_key_fallback_1: SecretStr | None = None  # Optional key
    groq_api_key: SecretStr | None = None
    groq_api_key_fallback_1: SecretStr | None = None 
    openai_api_key: SecretStr | None = None

    # Model Selection Defaults
    default_provider: str = "gemini"
    gemini_model: str = "gemini-3.6-flash"
    groq_model: str = "qwen/qwen3.8-27b"
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """Return the cached application settings instance.

    Args:
        None.

    Returns:
        Settings: Validated provider configuration.

    Example:
        settings = get_settings()
    """
    return Settings()