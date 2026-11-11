import json
from backend.app.schemas.workflow import ComplexityReport, SolutionPortfolio
from backend.app.agents.provider_runtime import invoke_structured

class Agent2ComplexityAnalyst:
    name = "agent_2_complexity_analyst"
    def run(self, portfolio: SolutionPortfolio, problem: dict):
        payload = {"problem": problem.get("title"), "variants": [v.model_dump() for v in portfolio.approaches]}
        report, trace = invoke_structured(self.name,
            "You are a rigorous algorithm analysis reviewer. Return one analysis for EVERY variant_id. Derive complexity step by step from loops, recursion, data structures and memory. Separate auxiliary space from input storage, include recursion stack, state assumptions and best/average/worst cases where meaningful. Correct false complexity claims.",
            "Analyze every implementation:\n" + json.dumps(payload, ensure_ascii=False), ComplexityReport)
        expected = {v.variant_id for v in portfolio.approaches}
        actual = {a.variant_id for a in report.analyses}
        if expected != actual:
            raise ValueError(f"Complexity coverage mismatch. Missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
        return report, trace
