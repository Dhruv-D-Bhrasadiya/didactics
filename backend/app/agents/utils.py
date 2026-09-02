import json
from typing import Any

from pydantic import ValidationError

from backend.app.schemas import IntentAnalysis


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


def is_rotatable_error(exc: Exception) -> bool:
    """Return whether an exception is likely recoverable with another key."""
    message = str(exc).lower()
    return any(keyword in message for keyword in ROTATABLE_ERROR_KEYWORDS)


def secret_value(value: Any) -> str | None:
    if value is None:
        return None
    return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)


def response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content).strip()


def parse_json_response(response: Any) -> IntentAnalysis:
    text = response_text(response)
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()

    try:
        return IntentAnalysis.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ValueError("The intent analyzer returned invalid JSON intent data") from exc


def build_gemini_llm(api_key: str, model_name: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
        max_retries=1,
    )


def build_groq_llm(api_key: str, model_name: str):
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=model_name,
        groq_api_key=api_key,
        temperature=0.2,
        max_retries=1,
    )


def build_openai_llm(api_key: str, model_name: str):
    from langchain.chat_models import ChatOpenAI

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        temperature=0.2,
        max_retries=1,
    )