"""Strict, bounded contracts exchanged between the six workflow agents."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class CodeVariant(StrictModel):
    variant_id: str = Field(min_length=2, max_length=48, pattern=r"^[a-zA-Z0-9_-]+$")
    algorithm_name: str = Field(min_length=2, max_length=100)
    strategy: str = Field(min_length=10, max_length=1200)
    intuition: str = Field(min_length=10, max_length=2000)
    steps: list[str] = Field(min_length=1, max_length=20)
    code: str = Field(min_length=10, max_length=30000)
    correctness_explanation: str = Field(min_length=10, max_length=3000)
    time_complexity_claim: str = Field(min_length=2, max_length=100)
    space_complexity_claim: str = Field(min_length=2, max_length=100)

class SolutionPortfolio(StrictModel):
    problem_summary: str = Field(min_length=10, max_length=2500)
    approaches: list[CodeVariant] = Field(min_length=1, max_length=8)
    recommended_variant_id: str
    comparison: list[str] = Field(default_factory=list, max_length=12)

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
    time_complexity: str = Field(min_length=2, max_length=100)
    time_derivation: list[str] = Field(min_length=1, max_length=15)
    space_complexity: str = Field(min_length=2, max_length=100)
    space_derivation: list[str] = Field(min_length=1, max_length=15)
    case_analysis: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list, max_length=12)

class ComplexityReport(StrictModel):
    analyses: list[ComplexityItem] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def unique_variants(self):
        ids = [item.variant_id for item in self.analyses]
        if len(ids) != len(set(ids)):
            raise ValueError("Complexity variant IDs must be unique")
        return self

class LessonScene(StrictModel):
    scene_id: str = Field(min_length=1, max_length=48, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=2, max_length=100)
    duration_seconds: int = Field(ge=5, le=90)
    objective: str = Field(min_length=5, max_length=300)
    narration: str = Field(min_length=10, max_length=5000)
    on_screen_text: list[str] = Field(min_length=1, max_length=10)
    visual_direction: str = Field(min_length=5, max_length=500)
    variant_id: str | None = None
    transition: Literal["cut", "fade", "slide", "transform"] = "cut"

class ScenePlan(StrictModel):
    lesson_title: str = Field(min_length=3, max_length=140)
    learning_outcomes: list[str] = Field(min_length=1, max_length=12)
    scenes: list[LessonScene] = Field(min_length=3, max_length=40)

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
    overall_summary: str = Field(min_length=5, max_length=2000)
    scene_results: list[QASceneResult] = Field(min_length=1, max_length=40)
    repair_tickets: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    media_checks: dict[str, Any] = Field(default_factory=dict)

class GenerateSessionRequest(StrictModel):
    problem_number: int = Field(gt=0, le=999999)
    language: Literal["python", "java", "c", "cpp"]
    dsa_proficiency: Literal["beginner", "intermediate", "advanced"]
    programming_proficiency: Literal["beginner", "intermediate", "advanced"]
    intent: Literal["solve", "prerequisites"] = "solve"
