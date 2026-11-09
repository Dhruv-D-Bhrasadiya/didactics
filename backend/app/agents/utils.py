import json
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ValidationError

from backend.app.schemas import (
    AgentExecutionTrace,
    PromptMessage,
    RequestUnderstanding,
    TokenUsage,
)


ROTATABLE_ERROR_KEYWORDS = [
    "quota",
    "429",
    "rate limit",
    "rate_limit",
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
    "service unavailable",
    "503",
    "502",
    "500",
    "internal server error",
]


class ModelResponseError(ValueError):
    """Report invalid structured model output while preserving its execution trace.

    The trace carries the raw response and request details for debugging.

    Example:
        error = ModelResponseError("Invalid output", trace)
    """

    def __init__(self, message: str, trace: AgentExecutionTrace):
        """Create an invalid-response error associated with its trace.

        Args:
            message: Human-readable description of the response failure.
            trace: Execution trace captured for the failed response.

        Returns:
            None: Initializes the exception and stores ``trace``.

        Example:
            error = ModelResponseError("Invalid output", trace)
        """
        super().__init__(message)
        self.trace = trace


def parse_structured_response(response: Any, output_type: type[BaseModel]) -> BaseModel:
    """Parse JSON model content and validate it against a Pydantic type.

    Args:
        response: Provider response or text-like response content.
        output_type: Pydantic model class used to validate parsed JSON.

    Returns:
        BaseModel: Validated instance of ``output_type``.

    Raises:
        ValueError: If response content is not valid JSON for the output type.

    Example:
        result = parse_structured_response(response, RequestUnderstanding)
    """
    text = response_text(response)
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()

    try:
        return output_type.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ValueError(f"The model returned invalid {output_type.__name__} data") from exc


def is_rotatable_error(exc: Exception) -> bool:
    """Determine whether an error may be recoverable with another API key.

    Args:
        exc: Exception raised during a model invocation.

    Returns:
        bool: Whether its message matches a configured retryable condition.

    Example:
        should_rotate = is_rotatable_error(RuntimeError("429 quota exceeded"))
    """
    message = str(exc).lower()
    return any(keyword in message for keyword in ROTATABLE_ERROR_KEYWORDS)


def secret_value(value: Any) -> str | None:
    """Extract a plain string from an optional secret-like setting.

    Args:
        value: A secret wrapper, string-like value, or ``None``.

    Returns:
        str | None: Unwrapped secret text, converted text, or ``None``.

    Example:
        key = secret_value(settings.groq_api_key)
    """
    if value is None:
        return None
    return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)


def response_text(response: Any) -> str:
    """Return normalized, whitespace-trimmed text from a model response.

    Args:
        response: Model response object or response content.

    Returns:
        str: Extracted response text with outer whitespace removed.

    Example:
        text = response_text(SimpleNamespace(content="  {}  "))
    """
    return raw_response_text(response).strip()


def raw_response_text(response: Any) -> str:
    """Extract response content as text without trimming whitespace.

    List content blocks are concatenated, using each mapping's ``text`` value.

    Args:
        response: Model response object or response content.

    Returns:
        str: String representation of the raw response content.

    Example:
        text = raw_response_text(SimpleNamespace(content=" {} "))
    """
    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def parse_json_response(response: Any) -> RequestUnderstanding:
    """Parse a model response as a request-understanding result.

    Args:
        response: Model response object or JSON response text.

    Returns:
        RequestUnderstanding: Validated Stage 1 request details.

    Raises:
        ValueError: If the response cannot be parsed or validated.

    Example:
        result = parse_json_response(response)
    """
    return parse_structured_response(response, RequestUnderstanding)


def _token_usage(response: Any) -> TokenUsage:
    """Normalize token usage fields from supported response metadata shapes.

    Args:
        response: Provider response with optional usage metadata.

    Returns:
        TokenUsage: Normalized counts and the original metadata mapping.

    Example:
        usage = _token_usage(SimpleNamespace(usage_metadata={"input_tokens": 4}))
    """
    usage: dict[str, Any] = {}
    metadata = getattr(response, "usage_metadata", None)
    if isinstance(metadata, dict):
        usage.update(metadata)

    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, dict):
        provider_usage = response_metadata.get("token_usage") or response_metadata.get(
            "usage"
        )
        if isinstance(provider_usage, dict):
            usage.update(provider_usage)
        provider_usage_metadata = response_metadata.get("usage_metadata")
        if isinstance(provider_usage_metadata, dict):
            usage.update(provider_usage_metadata)

    def first_int(*keys: str) -> int | None:
        """Return the first integer usage value among candidate field names.

        Args:
            *keys: Provider field names to inspect in priority order.

        Returns:
            int | None: First integer value excluding booleans, if present.

        Example:
            count = first_int("input_tokens", "prompt_tokens")
        """
        for key in keys:
            value = usage.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        return None

    return TokenUsage(
        input_tokens=first_int("input_tokens", "prompt_tokens", "promptTokenCount"),
        output_tokens=first_int(
            "output_tokens", "completion_tokens", "candidatesTokenCount"
        ),
        total_tokens=first_int("total_tokens", "totalTokenCount"),
        provider_usage=usage,
    )


def invoke_with_trace(
    agent: Any,
    messages: list[tuple[str, str]],
    agent_name: str,
) -> tuple[Any, AgentExecutionTrace]:
    """Invoke an agent with key rotation and capture its execution trace.

    Args:
        agent: Configured agent exposing keys, model, and output type.
        messages: Role/content pairs passed to the model.
        agent_name: Stable name recorded in the trace and errors.

    Returns:
        tuple[Any, AgentExecutionTrace]: Validated model result and trace.

    Raises:
        ModelResponseError: If the response cannot satisfy the output schema.
        Exception: If a non-rotatable error occurs or all keys fail.

    Example:
        result, trace = invoke_with_trace(agent, messages, "request_understanding")
    """
    attempts = 0
    for attempt in range(len(agent.api_keys)):
        attempts += 1
        started = perf_counter()
        try:
            response = agent.llm.invoke(messages)
        except Exception as exc:
            if not is_rotatable_error(exc) or attempt == len(agent.api_keys) - 1:
                raise
            agent.rotate_key()
            continue

        duration_ms = (perf_counter() - started) * 1000
        model_output = raw_response_text(response)
        if agent.output_type is None:
            raise TypeError("Agent output_type must be configured before invocation")
        try:
            output = parse_structured_response(response, agent.output_type)
        except ValueError as exc:
            trace = AgentExecutionTrace(
                agent_name=agent_name,
                provider=agent.provider,
                model_name=agent.model_name,
                request_messages=[
                    PromptMessage(role=role, content=content)
                    for role, content in messages
                ],
                raw_model_output=model_output,
                parsed_output={},
                token_usage=_token_usage(response),
                duration_ms=duration_ms,
                attempt_count=attempts,
            )
            raise ModelResponseError(
                f"{agent_name} returned invalid structured output; inspect error.trace",
                trace,
            ) from exc

        trace = AgentExecutionTrace(
            agent_name=agent_name,
            provider=agent.provider,
            model_name=agent.model_name,
            request_messages=[
                PromptMessage(role=role, content=content) for role, content in messages
            ],
            raw_model_output=model_output,
            parsed_output=output.model_dump(mode="json"),
            token_usage=_token_usage(response),
            duration_ms=duration_ms,
            attempt_count=attempts,
        )
        return output, trace

    raise RuntimeError(f"{agent_name} failed after exhausting configured API keys")


def build_gemini_llm(api_key: str, model_name: str):
    """Construct a Gemini chat model client with retry behavior disabled.

    Args:
        api_key: Gemini API credential.
        model_name: Exact Gemini model identifier.

    Returns:
        ChatGoogleGenerativeAI: Configured LangChain chat model.

    Example:
        llm = build_gemini_llm("key", "gemini-model")
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
        max_retries=0,
    )


def build_groq_llm(api_key: str, model_name: str):
    """Construct a Groq chat model client with retry behavior disabled.

    Args:
        api_key: Groq API credential.
        model_name: Exact Groq model identifier.

    Returns:
        ChatGroq: Configured LangChain chat model.

    Example:
        llm = build_groq_llm("key", "organization/model")
    """
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=model_name,
        groq_api_key=api_key,
        temperature=0.2,
        max_retries=0,
    )


def build_openai_llm(api_key: str, model_name: str):
    """Construct an OpenAI chat model client with retry behavior disabled.

    Args:
        api_key: OpenAI API credential.
        model_name: Exact OpenAI model identifier.

    Returns:
        ChatOpenAI: Configured LangChain chat model.

    Example:
        llm = build_openai_llm("key", "gpt-model")
    """
    from langchain.chat_models import ChatOpenAI

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        temperature=0.2,
        max_retries=0,
    )