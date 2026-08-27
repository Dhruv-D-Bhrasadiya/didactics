import unittest
from types import SimpleNamespace

from pydantic import SecretStr

from backend.app.agents.intent_analyzer_agent import (
	IntentAnalysis,
	IntentAnalyzerAgent,
	create_intent_analyzer_agent,
)
from backend.app.config import Settings


VALID_JSON = """{
	"domain": "computer science",
	"subdomain": "algorithms",
	"topic": "binary search",
	"subtopics": ["sorted arrays"],
	"modules": ["algorithm", "complexity"],
	"roadmap": ["explain", " demonstrate"],
	"deliverables": ["worked example"],
	"degree_of_explanation": "detailed",
	"audience": "beginner",
	"learning_objectives": ["implement binary search"],
	"assumptions": []
}"""


class FakeLLM:
	def __init__(self, response=None, error=None):
		self.response = response
		self.error = error
		self.messages = []

	def invoke(self, messages):
		self.messages.append(messages)
		if self.error:
			raise self.error
		return SimpleNamespace(content=self.response)


class IntentAnalyzerAgentTests(unittest.TestCase):
	def test_analyze_returns_validated_intent(self):
		llm = FakeLLM(VALID_JSON)
		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: llm)

		result = agent.analyze("Teach me binary search")

		self.assertIsInstance(result, IntentAnalysis)
		self.assertEqual(result.topic, "binary search")
		self.assertIn("Teach me binary search", llm.messages[0][1][1])

	def test_analyze_accepts_json_markdown_fence(self):
		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: FakeLLM(f"```json\n{VALID_JSON}\n```"))

		self.assertEqual(agent.analyze("Explain it").domain, "computer science")

	def test_rotates_once_per_key_on_rotatable_error(self):
		llms = {
			"first": FakeLLM(error=RuntimeError("429 quota exceeded")),
			"second": FakeLLM(VALID_JSON),
		}
		built_keys = []

		def builder(key, _model):
			built_keys.append(key)
			return llms[key]

		agent = IntentAnalyzerAgent("test-model", ["first", "second"], builder)

		result = agent.analyze("Explain it")

		self.assertEqual(result.topic, "binary search")
		self.assertEqual(built_keys, ["first", "second"])
		self.assertEqual(agent.current_key_index, 1)

	def test_non_rotatable_error_is_reraised(self):
		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: FakeLLM(error=ValueError("bad JSON")))

		with self.assertRaises(ValueError):
			agent.analyze("Explain it")

	def test_rejects_empty_query_and_keys(self):
		with self.assertRaises(ValueError):
			IntentAnalyzerAgent("test-model", [], lambda *_: FakeLLM())

		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: FakeLLM(VALID_JSON))
		with self.assertRaises(ValueError):
			agent.analyze("  ")

	def test_factory_unwraps_secret_keys(self):
		app_settings = Settings(
			gemini_api_key=SecretStr("primary"),
			gemini_api_key_fallback_1=SecretStr("fallback"),
		)

		agent = create_intent_analyzer_agent("gemini", "test-model", app_settings)

		self.assertEqual(agent.api_keys, ["primary", "fallback"])
		self.assertEqual(agent.model_name, "test-model")


if __name__ == "__main__":
	unittest.main()
