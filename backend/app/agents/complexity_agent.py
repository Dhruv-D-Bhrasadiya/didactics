"""Agent 2: complexity analysis for every solution variant."""
import json
from backend.app.agents.prompt_loader import load_prompt
from backend.app.agents.provider_runtime import invoke_structured
from backend.app.schemas.workflow import ComplexityReport, SolutionPortfolio

class Agent2ComplexityAnalyst:
    name = "agent_2_complexity_analyst"
    def run(self, portfolio: SolutionPortfolio, problem: dict | None = None):
        payload = {"approaches": [item.model_dump(mode="json") for item in portfolio.approaches]}
        report, trace = invoke_structured(self.name, load_prompt("agent_2_complexity"), "Analyze these implementations:\n" + json.dumps(payload, ensure_ascii=False), ComplexityReport)
        expected = {item.variant_id for item in portfolio.approaches}
        actual = {item.variant_id for item in report.analyses}
        if expected != actual:
            raise ValueError(f"Complexity coverage mismatch. Missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
        return report, trace
