import json
import unittest
from unittest.mock import patch
from backend.app.agents.solution_agent import Agent1SolutionStrategist
from backend.app.schemas.workflow import SolutionPortfolio

class AgentOneInputTests(unittest.TestCase):
    @patch("backend.app.agents.solution_agent.invoke_structured")
    def test_only_problem_fields_and_whitelisted_learner_settings_are_sent(self, invoke):
        portfolio = SolutionPortfolio(problem_summary="A simple test problem summary", approaches=[{"variant_id":"brute","algorithm_name":"Brute force","strategy":"Check all possible pairs","intuition":"Try each candidate pair until target is found","steps":["Check every pair"],"code":"def solve(nums):\n    return nums","correctness_explanation":"Every possible pair is checked","time_complexity_claim":"O(n^2)","space_complexity_claim":"O(1)"}], recommended_variant_id="brute")
        invoke.return_value = (portfolio, {"status":"success"})
        problem = {"statement_text":"Find a pair with target sum", "examples":[{"input":"[1,2], 3","output":"[0,1]"}], "constraints":["2 <= n <= 10^4"], "title":"Two Sum", "difficulty":"Easy", "topic_tags":["Array"], "metadata":{"noise":"not sent"}}
        Agent1SolutionStrategist().run(problem, {"language":"python","dsa_proficiency":"beginner","programming_proficiency":"intermediate","unrelated":"ignore"})
        user_prompt = invoke.call_args.args[2]
        problem_json = user_prompt.split("PROBLEM INPUT (only statement, examples, constraints):\n",1)[1].split("\nLEARNER SETTINGS:\n",1)[0]
        learner_json = user_prompt.split("\nLEARNER SETTINGS:\n",1)[1]
        self.assertEqual(set(json.loads(problem_json)), {"statement","examples","constraints"})
        self.assertEqual(set(json.loads(learner_json)), {"language","dsa_proficiency","programming_proficiency"})

if __name__ == "__main__": unittest.main()
