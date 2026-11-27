import os
from pathlib import Path
from services.leetcode_source import fetch_problem
from agents.solver_agent import SolverAgent
from agents.explainer_agent import ExplainerAgent

result = fetch_problem(1, "python")
print(result)

solver_agent = SolverAgent()
solver_agent_response = str(solver_agent.run(str(result)))
print(solver_agent_response)

explainer_agent = ExplainerAgent()
explainer_agent_response = explainer_agent.run(solver_agent_response)
print(explainer_agent_response)

output_path = Path("output/explainer_output.md")
output_path.parent.mkdir(parents=True, exist_ok=True)

with open("output/explainer_output.md", "w") as f:
    f.write(str(explainer_agent_response))