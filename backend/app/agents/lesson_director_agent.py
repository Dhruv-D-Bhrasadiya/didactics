"""Agent 3: lesson storyboard generation."""
import json
from backend.app.agents.prompt_loader import load_prompt
from backend.app.agents.provider_runtime import invoke_structured
from backend.app.schemas.workflow import ComplexityReport, ScenePlan, SolutionPortfolio

class Agent3LessonDirector:
    name = "agent_3_lesson_director"
    def run(self, problem: dict, portfolio: SolutionPortfolio, complexity: ComplexityReport, learner: dict):
        problem_input = {"statement": problem.get("statement_text") or problem.get("statement") or "", "examples": problem.get("examples") or [], "constraints": problem.get("constraints") or []}
        payload = {"problem": problem_input, "approaches": portfolio.model_dump(mode="json"), "complexity": complexity.model_dump(mode="json"), "learner": learner}
        prompt = load_prompt("agent_3_lesson_director")
        prompt += "\n\nMODE: " + ("PREREQUISITES. Teach required concepts first; do not expose the full target solution." if learner.get("intent") == "prerequisites" else "SOLVE. Follow the brute-force-to-optimized progression.")
        plan, trace = invoke_structured(self.name, prompt, "Create the scene plan:\n" + json.dumps(payload, ensure_ascii=False), ScenePlan)
        valid_ids = {item.variant_id for item in portfolio.approaches}
        for scene in plan.scenes:
            if scene.variant_id and scene.variant_id not in valid_ids:
                raise ValueError(f"Scene {scene.scene_id} references unknown variant {scene.variant_id}")
        return plan, trace
