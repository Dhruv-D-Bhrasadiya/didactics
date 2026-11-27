from pydantic import BaseModel, Field

class ExplainerSchema(BaseModel):
    prerequist: str = Field(
        ...,
        description="Explaination of Prerequist topic/algorithm in detailed",
    )
    question_explaination: str = Field(
        ..., 
        description="Explaination of the leetcode question, what is the question asking to solve"
    )
    example_explaination: str = Field(
        ...,
        description="Explaination of the leetcode question example, how did the output came to this, every example will have explaination you just have to explain it in little detailed and in simple language"
    )
    build_basic_intuition: str = Field(
        ...,
        description="Explain intuition to solve this question"
    )
    brute_force_explaination: str = Field(
        ...,
        description="Explain brute force approach in detialed and dry run the code on the examples"
    )
    intermediate_approach_explaination: str = Field(
        default_factory=list,
        description="Explain intermediate approach in detialed and dry run the code on the examples, explain it for all given intermediate approach"
    )
    optimized_approach_explaination: str = Field(
        default_factory=list,
        description="Explain optimized approach in detialed and dry run the code on the examples"
    )