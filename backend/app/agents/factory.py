from collections.abc import Callable

from backend.app.config import Settings
from backend.app.agents.utils import (
    build_gemini_llm,
    build_groq_llm,
    build_openai_llm,
    secret_value,
)


def resolve_agent_config(
    provider: str | None,
    model_name: str | None,
    app_settings: Settings,
) -> tuple[str, str, list[str], Callable]:
    """Resolve the selected provider, model, credentials, and client builder.

    Args:
        provider: Provider override, or ``None`` to use the configured default.
        model_name: Model override, or ``None`` to use the provider default.
        app_settings: Validated application credentials and defaults.

    Returns:
        tuple[str, str, list[str], Callable]: Provider, model ID, API keys,
            and the callable that builds that provider's model client.

    Raises:
        ValueError: If the provider is unsupported or configuration is missing.

    Example:
        provider, model, keys, builder = resolve_agent_config(
            "groq", "qwen/model", settings
        )
    """
    selected_provider = (provider or app_settings.default_provider).strip().lower()
    provider_config = {
        "gemini": (
            build_gemini_llm,
            app_settings.gemini_model,
            (app_settings.gemini_api_key, app_settings.gemini_api_key_fallback_1),
        ),
        "groq": (
            build_groq_llm,
            app_settings.groq_model,
            (app_settings.groq_api_key, app_settings.groq_api_key_fallback_1),
        ),
        "openai": (
            build_openai_llm,
            app_settings.openai_model,
            (app_settings.openai_api_key,),
        ),
    }
    if selected_provider not in provider_config:
        raise ValueError(f"Unsupported provider: {selected_provider}")

    builder, default_model, configured_keys = provider_config[selected_provider]
    keys = [key for key in (secret_value(value) for value in configured_keys) if key]
    if not keys:
        raise ValueError(f"No API key is configured for provider '{selected_provider}'")

    selected_model = model_name.strip() if model_name else default_model
    if not selected_model:
        raise ValueError(f"No model is configured for provider '{selected_provider}'")
    return selected_provider, selected_model, keys, builder
