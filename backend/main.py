import json

from dotenv import load_dotenv
from app.agents.solver_agent import SolutionAgent
from app.services.leetcode_source import fetch_problem

load_dotenv() 

problem = fetch_problem(1352, "java")
print(problem)

# Convert the problem dictionary to a string representation for the agent
problem_str = json.dumps(problem, indent=2)

a1 = SolutionAgent()
response = a1.run(problem_str)
print(response)