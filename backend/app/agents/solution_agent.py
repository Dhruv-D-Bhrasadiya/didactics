"""Agent 1: focused solution generation from the minimum problem context."""
import json
from backend.app.agents.prompt_loader import load_prompt
from backend.app.agents.provider_runtime import invoke_structured
from backend.app.schemas.workflow import SolutionPortfolio

class Agent1SolutionStrategist:
    name = "agent_1_solution_strategist"
    def run(self, problem: dict, learner: dict):
        problem_input = {
            "statement": problem.get("statement_text") or problem.get("statement") or "",
            "examples": problem.get("examples") or [],
            "constraints": problem.get("constraints") or [],
        }
        if not problem_input["statement"].strip():
            raise ValueError("Agent 1 requires a non-empty problem statement.")
        learner_input = {key: learner.get(key) for key in ("language", "dsa_proficiency", "programming_proficiency")}
        learner_input = {key: value for key, value in learner_input.items() if value is not None}
        user_prompt = "PROBLEM INPUT (only statement, examples, constraints):\n" + json.dumps(problem_input, ensure_ascii=False) + "\nLEARNER SETTINGS:\n" + json.dumps(learner_input, ensure_ascii=False)
        return invoke_structured(self.name, load_prompt("agent_1_solution"), user_prompt, SolutionPortfolio)
