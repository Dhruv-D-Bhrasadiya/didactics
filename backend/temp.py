from backend.app.agents.solver_agent import SolutionAgent
from backend.app.services.leetcode_source import fetch_problem

problem = fetch_problem(1, "python")
print(problem)

a1 = SolutionAgent()
response = a1.run(problem)
print(response)