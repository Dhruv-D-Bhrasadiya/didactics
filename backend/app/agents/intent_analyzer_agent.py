import json
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from backend.app.config import Settings, get_settings
from backend.app.prompts import load_prompt

# Error categories that trigger key rotation
# These are string fragments matched against exception messages.
# When any of these appear, we rotate to the next key instead of crashing.
ROTATABLE_ERROR_KEYWORDS = [
    "quota",
    "rate",
    "limit",
    "429",
    "exhausted",
    "resource_exhausted",
    "invalid api key",
    "authentication",
    "api key not valid",
    "permission denied",
    "403",
    "401",
    "timeout",
    "connection",
    "unavailable",
    "service unavailable",
    "503",
]


class IntentAnalysis(BaseModel):
    """Structured intent information returned by the analyzer."""

    domain: str
    subdomain: str = ""
    topic: str
    subtopics: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    degree_of_explanation: str = "moderate"
    audience: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

def _is_rotatable_error(exc: Exception) -> bool:
    """
        Returns True if the exception is a known rate-limit or auth error that should trigger key rotation rather than immediately crashing.
    """

    msg = str(exc).lower()
    return any(keyword in msg for keyword in ROTATABLE_ERROR_KEYWORDS)


def _secret_value(value: Any) -> str | None:
    if value is None:
        return None
    return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)


def _response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content).strip()


def _parse_json_response(response: Any) -> IntentAnalysis:
    text = _response_text(response)
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(text)
        return IntentAnalysis.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ValueError("The intent analyzer returned invalid JSON intent data") from exc


def _build_gemini_llm(api_key: str, model_name: str):
    """
        Creates a ChatGoogleGenerativeAI instance with the given key.
    """

    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
        max_retries=1,  # We handle retries ourselves via key rotation
    )


def _build_groq_llm(api_key: str, model_name: str):
    """
        Creates a ChatGroq instance with the given key.
    """

    from langchain_groq import ChatGroq
    return ChatGroq(
        model=model_name,
        groq_api_key=api_key,
        temperature=0.2,
        max_retries=1,
    )


def _build_openai_llm(api_key: str, model_name: str):
    """
        Creates a ChatOpenAI instance with the given key.
    """

    from langchain.chat_models import ChatOpenAI
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        temperature=0.2,
        max_retries=1,
    )


class BaseAgent:

    """
        Base class for agents that analyze user intent and generate responses.
    """

    def __init__(self, model_name: str, api_keys: list[str], llm_builder):
        if not api_keys:
            raise ValueError("At least one API key is required")
        self.model_name = model_name
        self.api_keys = [key for key in api_keys if key]
        if not self.api_keys:
            raise ValueError("At least one non-empty API key is required")
        self.llm_builder = llm_builder
        self.current_key_index = 0
        self.llm = self._build_llm()

    def _build_llm(self):
        """
            Builds the LLM instance using the current API key.
        """
        api_key = self.api_keys[self.current_key_index]
        return self.llm_builder(api_key, self.model_name)

    def rotate_key(self):
        """
            Rotates to the next API key in the list.
        """
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.llm = self._build_llm()


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