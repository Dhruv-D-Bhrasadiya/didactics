from agents.llm_factory import build_gemini_model
from schema.solver_schema import SolverSchema

class SolverAgent:
    def __init__(self):
        self.model = build_gemini_model()

    def run(self, user_prompt):
        
        with open("prompt/solver_prompt.md", "r") as f:
            solver_system_prompt = f.read()

        self.model = self.model.with_structured_output(SolverSchema)

        return self.model.invoke([("system", solver_system_prompt),("human", user_prompt),])

        