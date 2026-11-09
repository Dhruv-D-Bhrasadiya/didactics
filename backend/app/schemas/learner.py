"""Validated learner configuration contracts."""
from enum import Enum
from pydantic import BaseModel, ConfigDict


class ProgrammingLanguage(str, Enum):
    python = "python"
    java = "java"
    c = "c"
    cpp = "cpp"


class Proficiency(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class LearnerConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: ProgrammingLanguage
    dsa_proficiency: Proficiency
    programming_proficiency: Proficiency


def build_learning_profile(config: LearnerConfigRequest) -> dict:
    dsa_guidance = {
        Proficiency.beginner: "Define terminology and derive the approach incrementally; explain prerequisite data structures.",
        Proficiency.intermediate: "Assume common fundamentals; focus on observations, invariants, and trade-offs.",
        Proficiency.advanced: "Emphasize proof, invariants, asymptotic analysis, and optimization alternatives.",
    }
    programming_guidance = {
        Proficiency.beginner: "Explain every syntax construct actually used in the selected-language code, with annotated snippets.",
        Proficiency.intermediate: "Explain non-obvious syntax, APIs, data representation, and language-specific trade-offs.",
        Proficiency.advanced: "Use idiomatic concise code; focus on subtle semantics and performance.",
    }
    return {
        "language": config.language.value,
        "dsa_proficiency": config.dsa_proficiency.value,
        "programming_proficiency": config.programming_proficiency.value,
        "syntax_support": config.programming_proficiency == Proficiency.beginner,
        "dsa_guidance": dsa_guidance[config.dsa_proficiency],
        "programming_guidance": programming_guidance[config.programming_proficiency],
    }
