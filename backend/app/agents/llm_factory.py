from langchain.chat_models import init_chat_model
from app.configs.config import get_settings

settings = get_settings()

# Map providers to their corresponding API keys from Settings
PROVIDER_API_KEYS = {
    "google_genai": settings.gemini_api_key,
    "groq": settings.groq_api_key,
    "openai": settings.openai_api_key,
}

MODELS = {
    "agent_1_solution_strategist": {
        "provider": settings.default_provider,
        "model": settings.gemini_model,
    }
}


def get_model(agent_name: str):
    if agent_name not in MODELS:
        raise ValueError(f"Unknown agent: {agent_name}")

    config = MODELS[agent_name]
    provider = config["provider"]
    secret_key = PROVIDER_API_KEYS.get(provider)

    return init_chat_model(
        model=config["model"],
        model_provider=provider,
        api_key=secret_key.get_secret_value() if secret_key else None,
    )