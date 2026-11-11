from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CodeVariant(StrictModel):
    variant_id: str = Field(min_length=1)
    algorithm_name: str
    strategy: str
    intuition: str
    steps: list[str] = Field(min_length=1)
    code: str = Field(min_length=1)
    correctness_explanation: str
    time_complexity_claim: str
    space_complexity_claim: str

class SolutionPortfolio(StrictModel):
    problem_summary: str
    approaches: list[CodeVariant] = Field(min_length=1)
    recommended_variant_id: str
    comparison: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_variant_ids(self):
        ids = [item.variant_id for item in self.approaches]
        if len(ids) != len(set(ids)):
            raise ValueError("variant_id values must be unique")
        if self.recommended_variant_id not in ids:
            raise ValueError("recommended_variant_id must reference an approach")
        return self

class ComplexityItem(StrictModel):
    variant_id: str
    time_complexity: str
    time_derivation: list[str] = Field(min_length=1)
    space_complexity: str
    space_derivation: list[str] = Field(min_length=1)
    case_analysis: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)

class ComplexityReport(StrictModel):
    analyses: list[ComplexityItem] = Field(min_length=1)

class LessonScene(StrictModel):
    scene_id: str = Field(min_length=1)
    title: str
    duration_seconds: int = Field(ge=5, le=90)
    objective: str
    narration: str = Field(min_length=1)
    on_screen_text: list[str] = Field(min_length=1)
    visual_direction: str
    variant_id: str | None = None
    transition: str = "cut"

class ScenePlan(StrictModel):
    lesson_title: str
    learning_outcomes: list[str]
    scenes: list[LessonScene] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_scene_ids(self):
        ids = [scene.scene_id for scene in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("scene_id values must be unique")
        return self

class MediaResult(StrictModel):
    video_path: str | None = None
    audio_path: str | None = None
    rendered: bool = False
    audio_generated: bool = False
    warnings: list[str] = Field(default_factory=list)

class QASceneResult(StrictModel):
    scene_id: str
    passed: bool
    findings: list[str] = Field(default_factory=list)

class QAReport(StrictModel):
    passed: bool
    overall_summary: str
    scene_results: list[QASceneResult]
    repair_tickets: list[dict[str, Any]] = Field(default_factory=list)
    media_checks: dict[str, Any] = Field(default_factory=dict)

class GenerateSessionRequest(StrictModel):
    problem_number: int = Field(gt=0, le=999999)
    language: Literal["python", "java", "c", "cpp"]
    dsa_proficiency: Literal["beginner", "intermediate", "advanced"]
    programming_proficiency: Literal["beginner", "intermediate", "advanced"]
    intent: Literal["solve", "prerequisites"] = "solve"
