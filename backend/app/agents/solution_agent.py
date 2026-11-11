import json
from backend.app.schemas.workflow import SolutionPortfolio
from backend.app.agents.provider_runtime import invoke_structured

class Agent1SolutionStrategist:
    name = "agent_1_solution_strategist"
    def run(self, problem: dict, learner: dict):
        payload = {"problem": {k: problem.get(k) for k in ("problem_number","title","difficulty","statement_text","examples","constraints","topic_tags")}, "learner": learner}
        return invoke_structured(self.name,
            "You are an expert algorithms instructor. Return only schema-valid JSON. Never invent constraints. Produce a correct brute-force baseline first when meaningful, then explain each optimization step and include genuinely different algorithm families where they exist. Every approach needs complete executable code in the requested language, correctness reasoning and provisional complexity claims. Explain syntax for beginners. Use stable variant IDs.",
            "Create a solution portfolio:\n" + json.dumps(payload, ensure_ascii=False), SolutionPortfolio)
