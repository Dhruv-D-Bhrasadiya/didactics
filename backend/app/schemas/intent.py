from pydantic import BaseModel, Field


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