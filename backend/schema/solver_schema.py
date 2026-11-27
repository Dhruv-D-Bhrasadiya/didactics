from pydantic import BaseModel, Field


class Approach(BaseModel):
    code: str = Field(
        ...,
        description="Raw executable code only, without markdown backticks.",
    )
    intuition: str = Field(
        ...,
        description="Explanation covering intuition, base cases, and edge cases.",
    )
    time_complexity: str = Field(
        ..., description="Big-O time complexity (e.g., O(n log n))."
    )
    space_complexity: str = Field(
        ..., description="Big-O space complexity (e.g., O(n))."
    )


class SolverSchema(BaseModel):
    brute_force: Approach = Field(
        ..., description="The straightforward brute-force approach."
    )
    intermediate_approaches: list[Approach] = Field(
        default_factory=list,
        description="Zero, one, or two step-by-step optimizations leading toward the optimal solution.",
    )
    optimized: Approach = Field(
        ..., description="The most optimal approach in time and space."
    )
