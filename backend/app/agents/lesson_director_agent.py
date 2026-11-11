import json
from backend.app.schemas.workflow import ComplexityReport, ScenePlan, SolutionPortfolio
from backend.app.agents.provider_runtime import invoke_structured

class Agent3LessonDirector:
    name = "agent_3_lesson_director"
    def run(self, problem: dict, portfolio: SolutionPortfolio, complexity: ComplexityReport, learner: dict):
        payload = {"problem": {k: problem.get(k) for k in ("title","difficulty","statement_text","examples","constraints")}, "portfolio": portfolio.model_dump(), "complexity": complexity.model_dump(), "learner": learner}
        intent_rule = ("PREREQUISITES MODE: teach prerequisite concepts first, use small examples, do not reveal complete solution code in narration or on-screen text, and end with a bridge back to the problem." if learner.get("intent") == "prerequisites" else "SOLVE MODE: teach brute force first, optimize step by step, show every materially different algorithm and its code and complexity.")
        plan, trace = invoke_structured(self.name,
            "You are a video lesson director. " + intent_rule + " Create a coherent scene-by-scene teaching script. Include problem intuition, each approach and its complexity derivation, comparison and conclusion. Each scene needs unique scene_id, realistic duration, concise readable on-screen text, concrete visual direction and exact complete spoken narration. Refer only to supplied variant IDs. Adapt to learner proficiency. Return only schema-valid JSON.",
            "Create the complete scene plan:\n" + json.dumps(payload, ensure_ascii=False), ScenePlan)
        variant_ids = {v.variant_id for v in portfolio.approaches}
        for scene in plan.scenes:
            if scene.variant_id and scene.variant_id not in variant_ids:
                raise ValueError(f"Scene {scene.scene_id} references unknown variant {scene.variant_id}")
        return plan, trace
