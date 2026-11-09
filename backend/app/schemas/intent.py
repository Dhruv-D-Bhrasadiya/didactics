from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PromptMessage(BaseModel):
    """Represent one role/content pair sent to a language model.

    The model is used in execution traces to preserve the exact prompt
    messages supplied during an invocation.

    Example:
        message = PromptMessage(role="user", content="Explain binary search")
    """
    role: str
    content: str


class TokenUsage(BaseModel):
    """Store normalized token counts and provider-specific usage metadata.

    Token counts may be absent when a provider does not report them; raw
    provider fields remain available in ``provider_usage``.

    Example:
        usage = TokenUsage(input_tokens=12, output_tokens=8, total_tokens=20)
    """
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    provider_usage: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionTrace(BaseModel):
    """Capture prompts, outputs, usage, timing, and attempts for one run.

    This schema makes model behavior inspectable without coupling consumers
    to provider-specific response objects.

    Example:
        trace = AgentExecutionTrace(
            agent_name="request_understanding", provider="groq",
            model_name="qwen/model", request_messages=[],
            raw_model_output="{}", parsed_output={},
            token_usage=TokenUsage(), duration_ms=10, attempt_count=1,
        )
    """
    agent_name: str
    provider: str
    model_name: str
    request_messages: list[PromptMessage]
    raw_model_output: str
    parsed_output: dict[str, Any]
    token_usage: TokenUsage
    duration_ms: float
    attempt_count: int


class RequestUnderstanding(BaseModel):
    """Describe the learner request and the plan for responding to it.

    Fields capture topic, intent, learner context, concepts and dependencies,
    deliverables, constraints, ambiguity, clarifications, and confidence.
    ``validate_clarifications`` enforces consistency between those fields.

    Example:
        result = RequestUnderstanding(
            request_summary="Learn binary search",
            request_type="learn",
            topic="binary search",
            confidence=0.9,
            decision_summary="The topic is explicit.",
        )
    """

    model_config = ConfigDict(extra="forbid")

    request_summary: str
    request_type: Literal[
        "learn",
        "explain",
        "implement",
        "debug",
        "solve",
        "compare",
        "create",
        "other",
        "unclear",
    ]
    domain: str = ""
    subdomain: str = ""
    topic: str | None = None
    subtopics: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)

    learning_goal: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    learner_level: Literal[
        "beginner", "intermediate", "advanced", "mixed", "unknown"
    ] = "unknown"
    audience: str = ""
    prior_knowledge: list[str] = Field(default_factory=list)
    assumed_prerequisites: list[str] = Field(default_factory=list)
    explanation_depth: Literal[
        "brief", "overview", "moderate", "detailed", "deep", "unspecified"
    ] = "unspecified"
    degree_of_explanation: str = "unspecified"
    response_language: str | None = None
    requested_duration_minutes: int | None = Field(default=None, ge=1)
    mathematical_detail: Literal[
        "intuitive", "standard", "formal", "unspecified"
    ] = "unspecified"

    concepts: list[str] = Field(default_factory=list)
    concept_order: list[str] = Field(default_factory=list)
    concept_dependencies: dict[str, list[str]] = Field(default_factory=dict)
    deliverables: list[str] = Field(default_factory=list)
    preferred_format: list[str] = Field(default_factory=list)
    visual_preferences: list[str] = Field(default_factory=list)
    example_preferences: list[str] = Field(default_factory=list)
    programming_language: str | None = None
    constraints: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    conflicting_requirements: list[str] = Field(default_factory=list)

    is_actionable: bool = True
    ambiguity_level: Literal["none", "low", "medium", "high"] = "none"
    clarification_needed: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    decision_summary: str

    @model_validator(mode="after")
    def validate_clarifications(self):
        """Enforce cross-field clarification and concept consistency.

        Args:
            None.

        Returns:
            RequestUnderstanding: This validated instance.

        Raises:
            ValueError: If clarification, topic, conflict, or concept fields
                contradict one another.

        Example:
            result = RequestUnderstanding.model_validate(payload)
        """
        if self.clarification_needed and not self.clarification_questions:
            raise ValueError(
                "clarification_questions must be provided when clarification is needed"
            )
        if not self.clarification_needed and self.clarification_questions:
            raise ValueError(
                "clarification_needed must be true when questions are provided"
            )
        if self.topic is None and not self.clarification_needed:
            raise ValueError(
                "a missing topic must be accompanied by clarification questions"
            )
        if self.conflicting_requirements and not self.clarification_needed:
            raise ValueError(
                "unresolved conflicting requirements must trigger clarification"
            )
        if len(set(self.concepts)) != len(self.concepts):
            raise ValueError("concepts must not contain duplicates")
        if self.concepts and (
            len(self.concept_order) != len(self.concepts)
            or set(self.concept_order) != set(self.concepts)
        ):
            raise ValueError("concept_order must list each concept exactly once")
        if not set(self.concept_dependencies).issubset(self.concepts):
            raise ValueError("concept_dependencies keys must refer to listed concepts")
        return self


IntentAnalysis = RequestUnderstanding
