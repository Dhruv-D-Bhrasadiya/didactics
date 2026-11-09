import json

from backend.app.config import Settings, get_settings
from backend.app.prompts import load_prompt
from backend.app.schemas import (
    AgentExecutionTrace,
    RequestUnderstanding,
)
from backend.app.agents.base import BaseAgent
from backend.app.agents.factory import resolve_agent_config
from backend.app.agents.utils import (
    invoke_with_trace,
)


class RequestUnderstandingAgent(BaseAgent):
    """Analyze a learner request into the Stage 1 structured representation.

    This agent builds a schema-guided prompt, invokes a configured model, and
    returns validated request details with an optional execution trace.

    Example:
        agent = create_request_understanding_agent("groq")
        result = agent.analyze("Teach me binary search")
    """

    def __init__(
        self,
        model_name: str,
        api_keys: list[str],
        llm_builder,
        provider: str = "",
    ):
        """Initialize the model agent and load its system prompt.

        Args:
            model_name: Provider-specific model identifier.
            api_keys: Ordered credentials available for model invocation.
            llm_builder: Callable that creates a model client from key and name.
            provider: Provider identifier included in its trace.

        Returns:
            None: Initializes the request-understanding agent.

        Example:
            agent = RequestUnderstandingAgent("model", ["key"], builder, "groq")
        """
        super().__init__(model_name, api_keys, llm_builder, provider, RequestUnderstanding)
        self.system_prompt = load_prompt("request_understanding_agent.yaml")

    def analyze(self, query: str) -> RequestUnderstanding:
        """Analyze a non-empty learner query and return validated details.

        Args:
            query: Learner's request in natural language.

        Returns:
            RequestUnderstanding: Structured interpretation of the request.

        Example:
            result = agent.analyze("Teach me binary search in Java")
        """
        result, _ = self.analyze_with_trace(query)
        return result

    def analyze_with_trace(
        self, query: str
    ) -> tuple[RequestUnderstanding, AgentExecutionTrace]:
        """Analyze a query and retain prompt, response, and usage details.

        Args:
            query: Non-empty learner request to analyze.

        Returns:
            tuple[RequestUnderstanding, AgentExecutionTrace]: Validated
                interpretation and trace of the model execution.

        Raises:
            ValueError: If ``query`` is empty or not a string.
            ModelResponseError: If the model response violates the schema.

        Example:
            result, trace = agent.analyze_with_trace("Explain binary search")
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        schema = json.dumps(RequestUnderstanding.model_json_schema(), indent=2)
        user_prompt = (
            "Understand the learner's request and return one JSON object matching "
            "the complete Stage 1 schema. Cover the request type and topic, learner "
            "level and goals, prerequisites, scope, deliverables, concept inventory "
            "and learning order, and any ambiguity or clarification needed. If the "
            "request is vague or missing a topic, set topic to null and provide "
            "clarification questions instead of inventing details. Use unknown or "
            "unspecified values when the request does not provide enough evidence.\n"
            f"Schema:\n{schema}\n\nLearner request:\n{query.strip()}"
        )
        messages = [
            ("system", self.system_prompt),
            ("user", user_prompt),
        ]
        result, trace = invoke_with_trace(self, messages, "request_understanding")
        return RequestUnderstanding.model_validate(result), trace


def create_request_understanding_agent(
    provider: str | None = None,
    model_name: str | None = None,
    app_settings: Settings | None = None,
) -> RequestUnderstandingAgent:
    """Create a configured Stage 1 agent without making a network call.

    Args:
        provider: Optional provider override.
        model_name: Optional exact model identifier override.
        app_settings: Optional settings object; defaults to cached settings.

    Returns:
        RequestUnderstandingAgent: Ready-to-use request analyzer.

    Raises:
        ValueError: If provider configuration or credentials are invalid.

    Example:
        agent = create_request_understanding_agent("groq", "qwen/model")
    """
    provider, model, keys, builder = resolve_agent_config(
        provider, model_name, app_settings or get_settings()
    )
    return RequestUnderstandingAgent(model, keys, builder, provider)


IntentAnalysis = RequestUnderstanding
IntentAnalyzerAgent = RequestUnderstandingAgent
create_intent_analyzer_agent = create_request_understanding_agent