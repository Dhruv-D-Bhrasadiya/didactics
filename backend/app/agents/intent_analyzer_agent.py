import json

from backend.app.config import Settings, get_settings
from backend.app.prompts import load_prompt
from backend.app.schemas import IntentAnalysis
from backend.app.agents.base import BaseAgent
from backend.app.agents.utils import (
    build_gemini_llm as _build_gemini_llm,
    build_groq_llm as _build_groq_llm,
    build_openai_llm as _build_openai_llm,
    is_rotatable_error as _is_rotatable_error,
    parse_json_response as _parse_json_response,
    secret_value as _secret_value,
)


class IntentAnalyzerAgent(BaseAgent):
    """Classifies a learner's request into a plan for downstream agents."""

    def __init__(self, model_name: str, api_keys: list[str], llm_builder):
        super().__init__(model_name, api_keys, llm_builder)
        self.system_prompt = load_prompt("intent_analyzer_agent.yaml")

    def analyze(self, query: str) -> IntentAnalysis:
        """Analyze ``query`` and return validated, structured intent data."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        schema = json.dumps(IntentAnalysis.model_json_schema(), indent=2)
        user_prompt = (
            "Analyze this user query and return only a JSON object matching this schema.\n"
            f"Schema:\n{schema}\n\nUser query:\n{query.strip()}"
        )
        messages = [("system", self.system_prompt), ("user", user_prompt)]
        last_error: Exception | None = None

        for attempt in range(len(self.api_keys)):
            try:
                return _parse_json_response(self.llm.invoke(messages))
            except Exception as exc:
                last_error = exc
                if not _is_rotatable_error(exc) or attempt == len(self.api_keys) - 1:
                    raise
                self.rotate_key()

        raise RuntimeError("Intent analysis failed") from last_error


def create_intent_analyzer_agent(
    provider: str = "gemini",
    model_name: str | None = None,
    app_settings: Settings | None = None,
) -> IntentAnalyzerAgent:
    """Create an analyzer from application settings without making a network call."""
    app_settings = app_settings or get_settings()
    provider = provider.lower()
    provider_config = {
        "gemini": (
            _build_gemini_llm,
            "gemini-3.6-flash",
            (app_settings.gemini_api_key, app_settings.gemini_api_key_fallback_1),
        ),
        "groq": (
            _build_groq_llm,
            "llama-3.3-70b-versatile",
            (app_settings.groq_api_key, app_settings.groq_api_key_fallback_1),
        ),
        "openai": (
            _build_openai_llm,
            "gpt-4o-mini",
            (app_settings.openai_api_key,),
        ),
    }
    if provider not in provider_config:
        raise ValueError(f"Unsupported provider: {provider}")

    builder, default_model, configured_keys = provider_config[provider]
    keys = [key for key in (_secret_value(value) for value in configured_keys) if key]
    return IntentAnalyzerAgent(model_name or default_model, keys, builder)