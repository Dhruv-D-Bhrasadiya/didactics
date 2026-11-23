import json
from app.prompts.prompt_loader import load_prompt
from app.agents.llm_factory import get_model


class SolutionAgent:
    name = "agent_1_solution_strategist"

    def __init__(self):
        self.llm = get_model(self.name)
        self.system_prompt = load_prompt("solution_agent")

    def run(self, problem: str) -> str:
        if not problem:
            raise ValueError("Solution agent requires a non-empty problem description.")

        user_prompt = f"Please provide a solution for the following problem:\n{problem}"
        
        response = self.llm.invoke([
            ("system", self.system_prompt),
            ("human", user_prompt),
        ])

        return response.content
